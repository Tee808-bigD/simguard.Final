import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail || error.message || 'Request failed'
    const message = Array.isArray(detail) ? detail.map((item) => item.msg).join('; ') : detail
    return Promise.reject(new Error(message))
  },
)

export const submitTransaction = (data) => api.post('/transactions', data)
export const listTransactions = (params = {}) => api.get('/transactions', { params })
export const quickCheck = (data) => api.post('/fraud/check', data)
export const listAlerts = (params = {}) => api.get('/fraud/alerts', { params })
export const getDashboardStats = () => api.get('/dashboard/stats')
export const getTimeline = (hours = 24) => api.get('/dashboard/timeline', { params: { hours } })
export const getRiskDistribution = () => api.get('/dashboard/risk-distribution')
export const getDemoScenarios = () => api.get('/demo/scenarios')
export const runDemoScenario = (scenarioId) => api.post(`/demo/run-scenario/${scenarioId}`)
export const runShowcase = () => api.post('/demo/showcase')
export const resetDemo = () => api.post('/demo/reset')

export default api
