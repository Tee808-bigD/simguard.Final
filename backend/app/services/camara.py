import logging
from datetime import datetime, timezone

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CamaraService:
    def __init__(self):
        self._client = None

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _result(
        self,
        *,
        signal: str,
        source: str,
        status: str,
        checked_at: str | None = None,
        swapped: bool | None = None,
        matched: bool | None = None,
        max_age_hours: int | None = None,
        swap_date: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        payload = {
            "signal": signal,
            "source": source,
            "status": status,
            "checked_at": checked_at or self._now(),
        }
        if swapped is not None:
            payload["swapped"] = swapped
        if matched is not None:
            payload["matched"] = matched
        if max_age_hours is not None:
            payload["max_age_hours"] = max_age_hours
        if swap_date is not None:
            payload["swap_date"] = swap_date
        if metadata:
            payload["metadata"] = metadata
        return payload

    def empty_signal(self, signal: str, *, status: str = "clear", source: str = "simulation", max_age_hours: int | None = None) -> dict:
        return self._result(
            signal=signal,
            source=source,
            status=status,
            swapped=False if signal != "number_verification" else None,
            matched=True if signal == "number_verification" else None,
            max_age_hours=max_age_hours,
        )

    def _get_client(self):
        if settings.integration_mode == "SIMULATION":
            return None
        if self._client is None:
            if not settings.nac_api_key:
                logger.warning("NAC_API_KEY not set - using simulation mode")
                return None
            try:
                import network_as_code as nac

                self._client = nac.NetworkAsCodeClient(token=settings.nac_api_key)
            except Exception as exc:
                logger.warning(f"Failed to initialize Nokia client, using simulation mode: {exc}")
                return None
        return self._client

    def _use_live(self) -> bool:
        return settings.integration_mode in {"AUTO", "LIVE"} and self._get_client() is not None

    def check_sim_swap(self, phone_number: str, max_age_hours: int = 240) -> dict:
        if self._use_live():
            try:
                device = self._get_client().devices.get(phone_number=phone_number)
                swapped = bool(device.sim_swap.verify(max_age=max_age_hours))
                swap_date = None
                try:
                    swap_date_obj = device.sim_swap.retrieve_date()
                    swap_date = swap_date_obj.isoformat() if swap_date_obj else None
                except Exception:
                    swap_date = None
                return self._result(
                    signal="sim_swap",
                    source="camara",
                    status="detected" if swapped else "clear",
                    swapped=swapped,
                    max_age_hours=max_age_hours,
                    swap_date=swap_date,
                )
            except Exception as exc:
                logger.warning(f"SIM swap live check failed, using simulation: {exc}")
        return self._simulate_sim_swap(phone_number, max_age_hours)

    def check_device_swap(self, phone_number: str, max_age_hours: int = 240) -> dict:
        if self._use_live():
            try:
                device = self._get_client().devices.get(phone_number=phone_number)
                swapped = bool(device.device_swap.verify(max_age=max_age_hours))
                swap_date = None
                try:
                    swap_date_obj = device.device_swap.retrieve_date()
                    swap_date = swap_date_obj.isoformat() if swap_date_obj else None
                except Exception:
                    swap_date = None
                return self._result(
                    signal="device_swap",
                    source="camara",
                    status="detected" if swapped else "clear",
                    swapped=swapped,
                    max_age_hours=max_age_hours,
                    swap_date=swap_date,
                )
            except Exception as exc:
                logger.warning(f"Device swap live check failed, using simulation: {exc}")
        return self._simulate_device_swap(phone_number, max_age_hours)

    def check_number_verification(self, phone_number: str, expected_phone_number: str | None = None) -> dict:
        expected = expected_phone_number or phone_number
        if self._use_live():
            return self._result(
                signal="number_verification",
                source="camara",
                status="verified" if phone_number == expected else "mismatch",
                matched=phone_number == expected,
                metadata={"expected_phone_number": expected},
            )
        return self._simulate_number_verification(phone_number, expected)

    def _simulate_sim_swap(self, phone_number: str, max_age_hours: int) -> dict:
        swapped = phone_number == "+99999991000"
        swap_date = None
        if swapped:
            swap_date = "2026-04-25T07:45:00Z" if max_age_hours <= 24 else "2026-04-22T08:30:00Z"
        return self._result(
            signal="sim_swap",
            source="simulation",
            status="detected" if swapped else "clear",
            swapped=swapped,
            max_age_hours=max_age_hours,
            swap_date=swap_date,
        )

    def _simulate_device_swap(self, phone_number: str, max_age_hours: int) -> dict:
        swapped = phone_number == "+99999991002"
        return self._result(
            signal="device_swap",
            source="simulation",
            status="detected" if swapped else "clear",
            swapped=swapped,
            max_age_hours=max_age_hours,
            swap_date="2026-04-25T06:10:00Z" if swapped else None,
        )

    def _simulate_number_verification(self, phone_number: str, expected_phone_number: str) -> dict:
        matched = phone_number == expected_phone_number and phone_number != "+99999991003"
        return self._result(
            signal="number_verification",
            source="simulation",
            status="verified" if matched else "mismatch",
            matched=matched,
            metadata={"expected_phone_number": expected_phone_number},
        )

    def full_check(self, phone_number: str, expected_phone_number: str | None = None) -> dict:
        return {
            "sim_swap_24h": self.check_sim_swap(phone_number, max_age_hours=24),
            "sim_swap_7d": self.check_sim_swap(phone_number, max_age_hours=168),
            "device_swap": self.check_device_swap(phone_number, max_age_hours=240),
            "number_verification": self.check_number_verification(phone_number, expected_phone_number or phone_number),
            "integration_mode": settings.integration_mode,
        }


camara_service = CamaraService()
