package overview

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/state"
)

var (
	titleStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	panelStyle = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	mutedStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
	okStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
	warnStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	errStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
)

type Model struct {
	snapshot state.Snapshot
}

func New() Model {
	return Model{}
}

func (m Model) Title() string {
	return "Overview"
}

func (m Model) HelpLines() []string {
	return []string{
		"s  start/stop (docker) · reabre seleção (dev host/project)",
		"w  abrir Runtime",
		"d  abrir Databases",
		"l  abrir Logs",
		"t  run troubleshoot",
		"c  abrir Config",
	}
}

func (m Model) Init() tea.Cmd {
	return nil
}

func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	return m, nil
}

func (m Model) SetSnapshot(snapshot state.Snapshot) Model {
	m.snapshot = snapshot
	return m
}

// View renders the overview. Switches to a single-column layout for narrow
// terminals (width < 110) to avoid panel overflow.
func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}

	header := panelStyle.Width(width - 2).Render(m.headerView(width))

	if width < 110 {
		// Narrow: stack vertically, equal thirds of remaining height.
		bodyHeight := max(6, (height-8)/3)
		left   := panelStyle.Width(width - 2).Height(bodyHeight).Render(m.healthView())
		middle := panelStyle.Width(width - 2).Height(bodyHeight).Render(m.runtimeView())
		right  := panelStyle.Width(width - 2).Height(bodyHeight).Render(m.incidentsView())
		return lipgloss.JoinVertical(lipgloss.Left, header, left, middle, right)
	}

	// Wide: three columns side by side.
	bodyHeight := max(10, height-7)
	leftWidth   := max(28, width/3)
	middleWidth := max(28, width/3)
	rightWidth  := max(28, width-leftWidth-middleWidth-6)

	left   := panelStyle.Width(leftWidth).Height(bodyHeight).Render(m.healthView())
	middle := panelStyle.Width(middleWidth).Height(bodyHeight).Render(m.runtimeView())
	right  := panelStyle.Width(rightWidth).Height(bodyHeight).Render(m.incidentsView())
	return lipgloss.JoinVertical(lipgloss.Left, header,
		lipgloss.JoinHorizontal(lipgloss.Top, left, middle, right))
}

// headerView renders one field per line so that narrow terminals don't wrap
// the separator-joined summary into an unreadable mess.
func (m Model) headerView(width int) string {
	runtime := m.snapshot.Runtime
	fields := []string{
		fmt.Sprintf("mode: %s", fallback(runtime.Mode, "loading")),
		fmt.Sprintf("db: %s", fallback(runtime.ActiveDB, "not pinned")),
		fmt.Sprintf("local: %s", runtime.LocalURL),
		fmt.Sprintf("public: %s", runtime.PublicURL),
		fmt.Sprintf("config: %s", fallback(m.snapshot.Config.EnvPath, ".env")),
		fmt.Sprintf("refresh: %s", runtime.LastRefresh.Format("15:04:05")),
	}

	title := titleStyle.Render("Operational Snapshot")
	if width < 110 {
		// One field per line.
		return title + "\n" + strings.Join(fields, "\n")
	}
	// Single wide line with separator.
	return title + "  |  " + strings.Join(fields, "  |  ")
}

func (m Model) healthView() string {
	lines := []string{titleStyle.Render("Health")}
	for _, service := range m.snapshot.Services {
		lines = append(lines, fmt.Sprintf("%s %s", severityDot(service.Level), service.Name))
		lines = append(lines, mutedStyle.Render("  "+service.Status))
		if strings.TrimSpace(service.Detail) != "" {
			lines = append(lines, mutedStyle.Render("  "+service.Detail))
		}
	}
	if len(m.snapshot.Services) == 0 {
		lines = append(lines, mutedStyle.Render("No service health snapshot yet."))
	}
	return strings.Join(lines, "\n")
}

func (m Model) runtimeView() string {
	runtime := m.snapshot.Runtime
	lines := []string{
		titleStyle.Render("Runtime Summary"),
		fmt.Sprintf("backend: %s", fallback(runtime.Backend, "idle")),
		fmt.Sprintf("runtime: %s", fallback(runtime.RuntimeProfile, "unknown")),
		fmt.Sprintf("db backend: %s", fallback(runtime.DBBackend, "n/a")),
		fmt.Sprintf("config: %s", runtime.ConfigStatus),
		fmt.Sprintf("pid: %s", runtime.LocalPIDStatus),
		fmt.Sprintf("ports: %s", fallback(runtime.PortSummary, "none")),
		"",
		titleStyle.Render("Smoke"),
	}
	for _, result := range m.snapshot.Smoke {
		status := errStyle.Render("fail")
		if result.OK {
			status = okStyle.Render("ok  ")
		}
		lines = append(lines, fmt.Sprintf("%s %s (%s)", status, result.Name, result.Latency.Round(10_000_000)))
		if !result.OK && result.Error != "" {
			lines = append(lines, mutedStyle.Render("  "+result.Error))
		}
	}
	if len(runtime.Warnings) > 0 {
		lines = append(lines, "", titleStyle.Render("Warnings"))
		for _, w := range runtime.Warnings {
			lines = append(lines, warnStyle.Render("• "+w))
		}
	}
	return strings.Join(lines, "\n")
}

func (m Model) incidentsView() string {
	lines := []string{
		titleStyle.Render("Incidents / Next Step"),
		fallback(m.snapshot.Runtime.LastIncident, "sem incidentes"),
		"",
		warnStyle.Render("→ " + fallback(m.snapshot.Runtime.SuggestedNextStep, "abra Logs ou Doctor")),
	}
	if len(m.snapshot.Incidents) == 0 {
		lines = append(lines, "", okStyle.Render("Nenhum incidente ativo."))
		return strings.Join(lines, "\n")
	}
	for idx, incident := range m.snapshot.Incidents {
		if idx >= 4 {
			lines = append(lines, mutedStyle.Render(fmt.Sprintf("+ %d more", len(m.snapshot.Incidents)-4)))
			break
		}
		lines = append(lines, "", fmt.Sprintf("%s %s", severityDot(incident.Severity), incident.Summary))
		lines = append(lines, mutedStyle.Render(incident.Cause))
		lines = append(lines, warnStyle.Render("fix: "+incident.Suggestion))
	}
	return strings.Join(lines, "\n")
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
