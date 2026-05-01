import { useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  getDashboardStats,
  getDemoScenarios,
  getRiskDistribution,
  getTimeline,
  listAlerts,
  listTransactions,
  resetDemo,
  runDemoScenario,
  runShowcase,
  submitTransaction,
} from './api/client.js'
import { useWebSocket } from './hooks/useWebSocket.js'

const CURRENCIES = [
  { code: 'KES', label: 'Kenyan Shilling', symbol: 'KSh' },
  { code: 'UGX', label: 'Ugandan Shilling', symbol: 'USh' },
  { code: 'TZS', label: 'Tanzanian Shilling', symbol: 'TSh' },
  { code: 'ZMW', label: 'Zambian Kwacha', symbol: 'ZK' },
  { code: 'GHS', label: 'Ghanaian Cedi', symbol: 'GHs' },
  { code: 'NGN', label: 'Nigerian Naira', symbol: 'N' },
  { code: 'ZAR', label: 'South African Rand', symbol: 'R' },
  { code: 'USD', label: 'US Dollar', symbol: '$' },
  { code: 'EUR', label: 'Euro', symbol: 'EUR ' },
  { code: 'GBP', label: 'British Pound', symbol: 'GBP ' },
]

const DECISION_STYLE = {
  BLOCK: 'var(--danger)',
  FLAG_FOR_REVIEW: 'var(--warning)',
  APPROVE: 'var(--success)',
}

const STATUS_STYLE = {
  blocked: 'var(--danger)',
  flagged: 'var(--warning)',
  approved: 'var(--success)',
  pending: 'var(--muted)',
}

const DEFAULT_FORM = {
  phone_number: '',
  amount: '',
  currency: 'KES',
  transaction_type: 'send',
  recipient: '',
  agent_id: '',
}

const formatAmount = (value, currency) => {
  const symbol = CURRENCIES.find((item) => item.code === currency)?.symbol || `${currency} `
  return `${symbol}${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`
}

const formatTime = (value) =>
  value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--'

function App() {
  const [form, setForm] = useState(DEFAULT_FORM)
  const [result, setResult] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [alerts, setAlerts] = useState([])
  const [stats, setStats] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [distribution, setDistribution] = useState({})
  const [scenarios, setScenarios] = useState([])
  const [loading, setLoading] = useState(false)
  const [showcaseRunning, setShowcaseRunning] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')

  const refreshDashboard = async () => {
    const [statsRes, timelineRes, distRes, txRes, alertsRes, scenariosRes] = await Promise.all([
      getDashboardStats(),
      getTimeline(),
      getRiskDistribution(),
      listTransactions({ limit: 12 }),
      listAlerts({ limit: 10 }),
      getDemoScenarios(),
    ])
    setStats(statsRes.data)
    setTimeline(timelineRes.data)
    setDistribution(distRes.data)
    setTransactions(txRes.data)
    setAlerts(alertsRes.data)
    setScenarios(scenariosRes.data.scenarios || [])
  }

  useEffect(() => {
    refreshDashboard().catch((err) => setError(err.message))
  }, [])

  useWebSocket((message) => {
    if (message.type === 'transaction') {
      setTransactions((current) => [message.data, ...current.filter((item) => item.id !== message.data.id)].slice(0, 12))
      setResult(message.data)
      refreshDashboard().catch(() => {})
    }
    if (message.type === 'dashboard_reset') {
      setTransactions([])
      setAlerts([])
      setTimeline([])
      setDistribution({})
      setResult(null)
      refreshDashboard().catch(() => {})
    }
  })

  const distributionData = useMemo(
    () => [
      { name: 'Low', value: distribution.low || 0, color: '#31c48d' },
      { name: 'Medium', value: distribution.medium || 0, color: '#f5a524' },
      { name: 'High', value: distribution.high || 0, color: '#f97316' },
      { name: 'Critical', value: distribution.critical || 0, color: '#ef4444' },
    ],
    [distribution],
  )

  const handleSubmit = async (payload = null) => {
    const request = payload || {
      phone_number: form.phone_number.trim(),
      amount: Number(form.amount),
      currency: form.currency,
      transaction_type: form.transaction_type,
      recipient: form.recipient.trim() || undefined,
      agent_id: form.agent_id.trim() || undefined,
    }
    setLoading(true)
    setError('')
    setInfo('')
    try {
      const response = await submitTransaction(request)
      setResult(response.data)
      setInfo('Transaction analyzed successfully.')
      await refreshDashboard()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const hydrateScenario = (scenario) => {
    setForm({
      phone_number: scenario.payload.phone_number,
      amount: String(scenario.payload.amount),
      currency: scenario.payload.currency,
      transaction_type: scenario.payload.transaction_type,
      recipient: scenario.payload.recipient || '',
      agent_id: scenario.payload.agent_id || '',
    })
    setInfo(`${scenario.title} loaded into the agent form.`)
    setError('')
  }

  const runScenario = async (scenarioId) => {
    setLoading(true)
    setError('')
    setInfo('')
    try {
      const response = await runDemoScenario(scenarioId)
      setResult(response.data)
      setInfo('Scenario executed through the full fraud workflow.')
      await refreshDashboard()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleShowcase = async () => {
    setShowcaseRunning(true)
    setError('')
    setInfo('Showcase sequence started. Watch the live feed and result panel.')
    try {
      await runShowcase()
    } catch (err) {
      setError(err.message)
      setShowcaseRunning(false)
      return
    }
    window.setTimeout(() => setShowcaseRunning(false), 5000)
  }

  const handleReset = async () => {
    setLoading(true)
    setError('')
    try {
      await resetDemo()
      setForm(DEFAULT_FORM)
      setResult(null)
      setInfo('Demo state cleared.')
      await refreshDashboard()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const topSignals = result?.camara_results
    ? [
        ['SIM swap (24h)', result.camara_results.sim_swap_24h],
        ['SIM swap (7d)', result.camara_results.sim_swap_7d],
        ['Device swap', result.camara_results.device_swap],
        ['Number verification', result.camara_results.number_verification],
      ]
    : []

  return (
    <div className="shell">
      <section className="hero">
        <div>
          <div className="eyebrow">Africa Ignite Hackathon Prototype</div>
          <h1>SimGuard</h1>
          <p className="hero-copy">
            A guided anti-fraud demo for mobile money agents. SimGuard combines SIM swap, device swap, number verification,
            and agentic decisioning to produce an approve, flag, or block outcome that judges can understand fast.
          </p>
        </div>
        <div className="hero-meta">
          <MetaCard label="Mode" value={result?.integration_mode || 'SIMULATION'} note="Defaulted for demo reliability" />
          <MetaCard label="Next checkpoint" value="New Fraud System for 2026" note="Run Demo" />
          <MetaCard label="Prototype" value="Active Demo" note="Live demo plus pitch assets due" />
        </div>
      </section>

      <section className="band">
        <div className="band-header">
          <div>
            <div className="section-kicker">Guided Demo</div>
            <h2>Run the story judges need to see</h2>
          </div>
          <div className="actions">
            <button className="ghost-button" onClick={handleReset} disabled={loading}>Reset demo</button>
            <button className="primary-button" onClick={handleShowcase} disabled={loading || showcaseRunning}>
              {showcaseRunning ? 'Showcase running...' : 'Run 3-step showcase'}
            </button>
          </div>
        </div>
        <div className="scenario-grid">
          {scenarios.map((scenario) => (
            <article className="scenario-card" key={scenario.id}>
              <div className="scenario-top">
                <span className="pill" style={{ borderColor: DECISION_STYLE[scenario.decision] }}>{scenario.decision.replaceAll('_', ' ')}</span>
                <span className="micro-copy">{scenario.payload.currency} {scenario.payload.amount}</span>
              </div>
              <h3>{scenario.title}</h3>
              <p>{scenario.summary}</p>
              <div className="scenario-actions">
                <button className="ghost-button" onClick={() => hydrateScenario(scenario)} disabled={loading}>Load form</button>
                <button className="secondary-button" onClick={() => runScenario(scenario.id)} disabled={loading}>Run scenario</button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="workspace">
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="section-kicker">Primary Workflow</div>
              <h2>Agent transaction check</h2>
            </div>
            <span className="status-chip">One transaction, three trust signals, one decision</span>
          </div>
          <div className="form-grid">
            <Field label="Customer phone (E.164)">
              <input value={form.phone_number} placeholder="+254712345678" onChange={(e) => setForm({ ...form, phone_number: e.target.value })} />
            </Field>
            <Field label="Amount">
              <input type="number" min="0" value={form.amount} placeholder="0.00" onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            </Field>
            <Field label="Currency">
              <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
                {CURRENCIES.map((item) => <option key={item.code} value={item.code}>{item.code} - {item.label}</option>)}
              </select>
            </Field>
            <Field label="Transaction type">
              <select value={form.transaction_type} onChange={(e) => setForm({ ...form, transaction_type: e.target.value })}>
                <option value="send">Send money</option>
                <option value="receive">Receive</option>
                <option value="withdraw">Withdraw</option>
                <option value="deposit">Deposit</option>
              </select>
            </Field>
            <Field label="Recipient">
              <input value={form.recipient} placeholder="Merchant or recipient" onChange={(e) => setForm({ ...form, recipient: e.target.value })} />
            </Field>
            <Field label="Agent ID">
              <input value={form.agent_id} placeholder="AGENT-KE-101" onChange={(e) => setForm({ ...form, agent_id: e.target.value })} />
            </Field>
          </div>
          {error && <div className="notice danger">{error}</div>}
          {info && <div className="notice success">{info}</div>}
          <div className="actions">
            <button
              className="primary-button"
              onClick={() => handleSubmit()}
              disabled={loading || !form.phone_number || !form.amount}
            >
              {loading ? 'Analyzing...' : 'Check transaction'}
            </button>
          </div>
        </div>

        <div className="panel decision-panel">
          <div className="panel-header">
            <div>
              <div className="section-kicker">Decision Output</div>
              <h2>Fraud response</h2>
            </div>
            {result && <span className="status-chip">{result.source}</span>}
          </div>
          {!result && <EmptyState text="Run a scenario or submit a transaction to see the telecom risk analysis." />}
          {result && (
            <div className="decision-stack">
              <div className="decision-banner" style={{ borderColor: DECISION_STYLE[result.ai_decision] }}>
                <div>
                  <div className="decision-label">Decision</div>
                  <div className="decision-value">{result.ai_decision.replaceAll('_', ' ')}</div>
                </div>
                <div className="decision-metrics">
                  <MetricCard label="Risk score" value={String(result.risk_score)} />
                  <MetricCard label="Confidence" value={`${result.confidence || '--'}%`} />
                  <MetricCard label="Amount" value={formatAmount(result.amount, result.currency)} />
                </div>
              </div>
              <p className="lead">{result.primary_reason}</p>
              <p className="muted-copy">{result.ai_explanation}</p>
              <div className="action-list">
                {(result.recommended_actions || []).map((item) => <div className="action-item" key={item}>{item}</div>)}
              </div>
              <div className="signal-grid">
                {topSignals.map(([label, signal]) => (
                  <SignalCard key={label} label={label} signal={signal} />
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="metrics-row">
        <MetricPanel label="Blocked" value={stats?.total_blocked ?? 0} note="High-confidence fraud stops" tone="danger" />
        <MetricPanel label="Flagged" value={stats?.total_flagged ?? 0} note="Needs a human check" tone="warning" />
        <MetricPanel label="Approved" value={stats?.total_approved ?? 0} note="Low-risk customers" tone="success" />
        <MetricPanel label="Approval rate" value={`${stats?.approval_rate ?? 0}%`} note="Across demo traffic" tone="neutral" />
      </section>

      <section className="analytics">
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="section-kicker">Live Dashboard</div>
              <h2>Recent transaction trend</h2>
            </div>
          </div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={timeline}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="time" tick={{ fill: '#9ca3af', fontSize: 12 }} tickFormatter={(value) => value.slice(11, 16)} />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} allowDecimals={false} />
                <Tooltip />
                <Line type="monotone" dataKey="total" stroke="#7c3aed" strokeWidth={2.5} dot={false} />
                <Line type="monotone" dataKey="blocked" stroke="#ef4444" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="section-kicker">Risk Mix</div>
              <h2>Distribution snapshot</h2>
            </div>
          </div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={distributionData} dataKey="value" nameKey="name" innerRadius={64} outerRadius={96} paddingAngle={4}>
                  {distributionData.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="legend">
              {distributionData.map((entry) => (
                <div key={entry.name} className="legend-item">
                  <span className="legend-dot" style={{ background: entry.color }} />
                  <span>{entry.name}</span>
                  <strong>{entry.value}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="analytics">
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="section-kicker">Live Feed</div>
              <h2>Recent transactions</h2>
            </div>
          </div>
          <div className="table-list">
            {transactions.map((transaction) => (
              <div className="table-row" key={transaction.id}>
                <div>
                  <div className="row-title">{transaction.phone_number}</div>
                  <div className="row-subtitle">{transaction.transaction_type} · {formatTime(transaction.created_at)}</div>
                </div>
                <div className="row-amount">{formatAmount(transaction.amount, transaction.currency)}</div>
                <span className="pill" style={{ borderColor: STATUS_STYLE[transaction.status] }}>{transaction.status}</span>
              </div>
            ))}
            {!transactions.length && <EmptyState text="No transactions yet. The guided scenarios will populate this feed." compact />}
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="section-kicker">Alert Feed</div>
              <h2>Fraud signals</h2>
            </div>
          </div>
          <div className="table-list">
            {alerts.map((alert) => (
              <div className="table-row" key={alert.id}>
                <div>
                  <div className="row-title">{alert.alert_type.replaceAll('_', ' ')}</div>
                  <div className="row-subtitle">{alert.phone_number} · {alert.risk_level}</div>
                </div>
                <div className="row-amount">{alert.risk_score}/100</div>
                <span className="pill" style={{ borderColor: STATUS_STYLE[alert.action_taken] }}>{alert.action_taken}</span>
              </div>
            ))}
            {!alerts.length && <EmptyState text="Alerts appear here when risk crosses the medium threshold." compact />}
          </div>
        </div>
      </section>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  )
}

function MetaCard({ label, value, note }) {
  return (
    <div className="meta-card">
      <div className="section-kicker">{label}</div>
      <div className="meta-value">{value}</div>
      <p>{note}</p>
    </div>
  )
}

function MetricPanel({ label, value, note, tone }) {
  return (
    <div className={`metric-panel ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{note}</p>
    </div>
  )
}

function MetricCard({ label, value }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function SignalCard({ label, signal }) {
  const isVerification = Object.prototype.hasOwnProperty.call(signal, 'matched')
  const active = isVerification ? signal.matched : !signal.swapped
  return (
    <div className="signal-card">
      <div className="signal-top">
        <span>{label}</span>
        <span className="micro-copy">{signal.source}</span>
      </div>
      <strong>{signal.status.replaceAll('_', ' ')}</strong>
      <p>{signal.swap_date ? `Event at ${signal.swap_date}` : `Checked at ${formatTime(signal.checked_at)}`}</p>
      <span className="pill" style={{ borderColor: active ? 'var(--success)' : 'var(--danger)' }}>
        {active ? 'trusted' : 'risky'}
      </span>
    </div>
  )
}

function EmptyState({ text, compact = false }) {
  return <div className={`empty-state ${compact ? 'compact' : ''}`}>{text}</div>
}

export default App
