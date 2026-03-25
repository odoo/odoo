package dashboard

import (
	"fmt"
	"sort"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/docker"
	"github.com/kodoo/kodoo-tui/internal/envconfig"
	"github.com/kodoo/kodoo-tui/internal/event"
	"github.com/kodoo/kodoo-tui/internal/state"
)

var (
	titleStyle    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	panelStyle    = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	mutedStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
	okStyle       = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
	warnStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	errStyle      = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	neutralStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("81"))
	selectedStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
)

type Model struct {
	cfg      *envconfig.Config
	snapshot state.Snapshot
}

func New(cfg *envconfig.Config) Model {
	return Model{cfg: cfg}
}

func (m Model) Title() string {
	return "Dashboard"
}

func (m Model) HelpLines() []string {
	return []string{
		"s start/stop contextual",
		"w open Runtime",
		"d open Databases",
		"l open Logs",
		"t run troubleshoot",
		"c open Config",
	}
}

func (m Model) Init() tea.Cmd {
	return nil
}

func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "t":
			return m, requestCmd(event.RequestMakeTargetMsg{
				Target:      "troubleshoot",
				Description: "Run the detailed diagnostics target.",
				RelevantKeys: []string{
					"DOMAIN",
				},
			})
		}
	}
	return m, nil
}

func (m Model) SetConfig(cfg *envconfig.Config) Model {
	m.cfg = cfg
	return m
}

func (m Model) SetSnapshot(snapshot state.Snapshot) Model {
	m.snapshot = snapshot
	return m
}

func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}

	header := panelStyle.Width(width - 2).Render(m.headerView())
	bodyHeight := max(10, height-7)
	leftWidth := max(34, width/3)
	middleWidth := max(34, width/3)
	rightWidth := max(30, width-leftWidth-middleWidth-6)

	left := panelStyle.Width(leftWidth).Height(bodyHeight).Render(m.healthView())
	middle := panelStyle.Width(middleWidth).Height(bodyHeight).Render(m.tenantsView())
	right := panelStyle.Width(rightWidth).Height(bodyHeight).Render(m.securityAndResourcesView())
	return lipgloss.JoinVertical(lipgloss.Left, header, lipgloss.JoinHorizontal(lipgloss.Top, left, middle, right))
}

func (m Model) headerView() string {
	runtime := m.snapshot.Runtime
	lines := []string{
		titleStyle.Render("Operational Dashboard"),
		fmt.Sprintf("mode: %s", fallback(runtime.Mode, "loading")),
		fmt.Sprintf("runtime: %s", fallback(runtime.RuntimeProfile, "unknown")),
		fmt.Sprintf("active db: %s", fallback(runtime.ActiveDB, fallback(m.cfg.ProdDBName, "not pinned"))),
		fmt.Sprintf("local: %s", runtime.LocalURL),
		fmt.Sprintf("public: %s", runtime.PublicURL),
		fmt.Sprintf("refresh: %s", runtime.LastRefresh.Format("15:04:05")),
	}
	return strings.Join(lines, "  |  ")
}

func (m Model) healthView() string {
	lines := []string{
		titleStyle.Render("Health / Status"),
		fmt.Sprintf("config: %s", m.snapshot.Runtime.ConfigStatus),
		fmt.Sprintf("ports: %s", fallback(m.snapshot.Runtime.PortSummary, "no published ports")),
		"",
		titleStyle.Render("Services"),
	}
	for _, service := range m.snapshot.Services {
		lines = append(lines, fmt.Sprintf("%s %s", severityDot(service.Level), service.Name))
		lines = append(lines, mutedStyle.Render("  "+service.Status))
		if detail := strings.TrimSpace(service.Detail); detail != "" {
			lines = append(lines, mutedStyle.Render("  "+detail))
		}
	}

	lines = append(lines, "", titleStyle.Render("Smoke"))
	if len(m.snapshot.Smoke) == 0 {
		lines = append(lines, mutedStyle.Render("No smoke probes available."))
	} else {
		for _, result := range m.snapshot.Smoke {
			status := errStyle.Render("fail")
			if result.OK {
				status = okStyle.Render("ok")
			}
			lines = append(lines, fmt.Sprintf("%s %s (%s)", status, result.Name, result.Latency.Round(10_000_000)))
			if !result.OK && result.Error != "" {
				lines = append(lines, mutedStyle.Render("  "+result.Error))
			}
		}
	}
	return strings.Join(lines, "\n")
}

func (m Model) tenantsView() string {
	rootDB := fallback(m.cfg.ProdDBName, "kodoo")
	adminHost := fallback(m.cfg.Domain, "kodoo.online")
	filter := fallback(m.snapshot.Config.ProdDBFilter, fallback(m.cfg.ProdDBFilter, "^%d$"))
	tenants := tenantDatabases(m.snapshot.Databases, rootDB)

	lines := []string{
		titleStyle.Render("Tenant Routing"),
		fmt.Sprintf("db manager: %s", enabledLabel(m.snapshot.Config.ProdListDB)),
		fmt.Sprintf("dbfilter: %s", filter),
		fmt.Sprintf("admin host: %s -> %s", adminHost, rootDB),
	}
	if len(tenants) > 0 {
		lines = append(lines, fmt.Sprintf("tenant example: %s -> %s", tenantHost(tenants[0], adminHost), tenants[0]))
		lines = append(lines, fmt.Sprintf("client dbs: %d", len(tenants)))
	} else {
		lines = append(lines, "tenant example: create a new client DB and use <db>."+adminHost)
		lines = append(lines, "client dbs: 0")
	}

	lines = append(lines, "", titleStyle.Render("Client Databases"))
	if len(tenants) == 0 {
		lines = append(lines, mutedStyle.Render("No client-specific databases detected yet."))
		lines = append(lines, mutedStyle.Render("Use /web/database/manager to create one DB per customer."))
	} else {
		limit := min(6, len(tenants))
		for idx := 0; idx < limit; idx++ {
			name := tenants[idx]
			lines = append(lines, selectedStyle.Render(name))
			lines = append(lines, mutedStyle.Render("  host: "+tenantHost(name, adminHost)))
		}
		if len(tenants) > limit {
			lines = append(lines, mutedStyle.Render(fmt.Sprintf("+ %d more client DBs", len(tenants)-limit)))
		}
	}

	lines = append(lines, "", titleStyle.Render("Operator Flow"))
	lines = append(lines, "1. Create one DB per customer in the native manager.")
	lines = append(lines, "2. Install only the addons required for that tenant.")
	lines = append(lines, "3. Publish the tenant at <db>."+adminHost+".")
	lines = append(lines, "4. In Cloudflare, map *."+adminHost+" -> http://nginx:80.")
	return strings.Join(lines, "\n")
}

func (m Model) securityAndResourcesView() string {
	lines := []string{
		titleStyle.Render("Security / Resources"),
		fmt.Sprintf("token: %s", presenceLabel(strings.TrimSpace(m.cfg.CloudflaredToken) != "")),
		fmt.Sprintf("lan bind: %s", fallback(m.cfg.LocalBindHost, "127.0.0.1")),
		fmt.Sprintf("dbfilter posture: %s", dbFilterPosture(fallback(m.cfg.ProdDBFilter, m.snapshot.Config.ProdDBFilter))),
		fmt.Sprintf("manager exposure: %s", managerExposureLabel(m.snapshot.Config.ProdListDB, fallback(m.cfg.ProdDBFilter, m.snapshot.Config.ProdDBFilter))),
		fmt.Sprintf("env source: %s", fallback(m.snapshot.Config.EnvPath, ".env")),
		"",
		titleStyle.Render("Resource Usage"),
	}

	stats := append([]stateLikeStat(nil), convertStats(m.snapshot.Stats)...)
	sort.Slice(stats, func(i, j int) bool {
		return stats[i].CPUPercent > stats[j].CPUPercent
	})
	if len(stats) == 0 {
		lines = append(lines, mutedStyle.Render("No docker stats available."))
	} else {
		for _, stat := range stats {
			lines = append(lines, fmt.Sprintf("%s  CPU %5.1f%%  MEM %5.1f%%", stat.Name, stat.CPUPercent, stat.MemPercent))
			if stat.MemUsage != "" {
				lines = append(lines, mutedStyle.Render("  "+stat.MemUsage))
			}
		}
	}

	lines = append(lines, "", titleStyle.Render("Incidents / Next Step"))
	lines = append(lines, m.snapshot.Runtime.LastIncident)
	lines = append(lines, warnStyle.Render("next: "+fallback(m.snapshot.Runtime.SuggestedNextStep, "open Logs or Doctor")))
	if len(m.snapshot.Incidents) > 0 {
		for idx, incident := range m.snapshot.Incidents {
			if idx >= 3 {
				break
			}
			lines = append(lines, "", fmt.Sprintf("%s %s", severityDot(incident.Severity), incident.Summary))
			lines = append(lines, mutedStyle.Render(incident.Cause))
		}
	}
	return strings.Join(lines, "\n")
}

type stateLikeStat struct {
	Name       string
	CPUPercent float64
	MemPercent float64
	MemUsage   string
}

func convertStats(stats []docker.Stat) []stateLikeStat {
	rows := make([]stateLikeStat, 0, len(stats))
	for _, stat := range stats {
		rows = append(rows, stateLikeStat{
			Name:       stat.Name,
			CPUPercent: stat.CPUPercent,
			MemPercent: stat.MemPercent,
			MemUsage:   stat.MemUsage,
		})
	}
	return rows
}

func tenantDatabases(rows []state.DatabaseInfo, rootDB string) []string {
	tenants := make([]string, 0, len(rows))
	for _, row := range rows {
		if row.Backend != "docker" {
			continue
		}
		switch row.Name {
		case "", "postgres", rootDB:
			continue
		}
		tenants = append(tenants, row.Name)
	}
	sort.Strings(tenants)
	return tenants
}

func tenantHost(dbName, domain string) string {
	return dbName + "." + domain
}

func severityDot(level state.Severity) string {
	switch level {
	case state.SeverityCritical:
		return errStyle.Render("●")
	case state.SeverityWarning:
		return warnStyle.Render("●")
	default:
		return okStyle.Render("●")
	}
}

func enabledLabel(value bool) string {
	if value {
		return okStyle.Render("enabled")
	}
	return warnStyle.Render("disabled")
}

func presenceLabel(value bool) string {
	if value {
		return okStyle.Render("present")
	}
	return warnStyle.Render("missing")
}

func dbFilterPosture(filter string) string {
	if strings.Contains(filter, "%d") {
		return okStyle.Render("tenant-safe")
	}
	if strings.TrimSpace(filter) == "" {
		return warnStyle.Render("unset")
	}
	return errStyle.Render("broad")
}

func managerExposureLabel(listDB bool, filter string) string {
	if !listDB {
		return neutralStyle.Render("closed")
	}
	if strings.Contains(filter, "%d") {
		return okStyle.Render("open with tenant filter")
	}
	return errStyle.Render("open and broad")
}

func requestCmd(msg tea.Msg) tea.Cmd {
	return func() tea.Msg { return msg }
}

func fallback(value, or string) string {
	if strings.TrimSpace(value) == "" {
		return or
	}
	return value
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
