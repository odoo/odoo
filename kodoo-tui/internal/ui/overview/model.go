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
	return m, nil
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
	leftWidth := max(28, width/3)
	middleWidth := max(28, width/3)
	rightWidth := max(28, width-leftWidth-middleWidth-6)

	left := panelStyle.Width(leftWidth).Height(bodyHeight).Render(m.healthView())
	middle := panelStyle.Width(middleWidth).Height(bodyHeight).Render(m.runtimeView())
	right := panelStyle.Width(rightWidth).Height(bodyHeight).Render(m.incidentsView())
	return lipgloss.JoinVertical(lipgloss.Left, header, lipgloss.JoinHorizontal(lipgloss.Top, left, middle, right))
}

func (m Model) headerView() string {
	runtime := m.snapshot.Runtime
	lines := []string{
		titleStyle.Render("Operational Snapshot"),
		fmt.Sprintf("mode: %s", runtime.Mode),
		fmt.Sprintf("database: %s", fallback(runtime.ActiveDB, "not pinned")),
		fmt.Sprintf("local: %s", runtime.LocalURL),
		fmt.Sprintf("public: %s", runtime.PublicURL),
		fmt.Sprintf("config: %s", fallback(m.snapshot.Config.EnvPath, ".env")),
		fmt.Sprintf("refresh: %s", runtime.LastRefresh.Format("15:04:05")),
	}
	return strings.Join(lines, "  |  ")
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
		fmt.Sprintf("backend: %s", runtime.Backend),
		fmt.Sprintf("runtime: %s", runtime.RuntimeProfile),
		fmt.Sprintf("db backend: %s", fallback(runtime.DBBackend, "n/a")),
		fmt.Sprintf("config: %s", runtime.ConfigStatus),
		fmt.Sprintf("pid: %s", runtime.LocalPIDStatus),
		fmt.Sprintf("ports: %s", runtime.PortSummary),
		"",
		titleStyle.Render("Smoke"),
	}
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
	if len(runtime.Warnings) > 0 {
		lines = append(lines, "", titleStyle.Render("Warnings"))
		for _, warning := range runtime.Warnings {
			lines = append(lines, warnStyle.Render("• "+warning))
		}
	}
	return strings.Join(lines, "\n")
}

func (m Model) incidentsView() string {
	lines := []string{
		titleStyle.Render("Incidents / Next Step"),
		m.snapshot.Runtime.LastIncident,
		"",
		"Suggested action:",
		warnStyle.Render(m.snapshot.Runtime.SuggestedNextStep),
	}
	if len(m.snapshot.Incidents) == 0 {
		lines = append(lines, "", okStyle.Render("No active incidents."))
		return strings.Join(lines, "\n")
	}
	for idx, incident := range m.snapshot.Incidents {
		if idx >= 4 {
			break
		}
		lines = append(lines, "", fmt.Sprintf("%s %s", severityDot(incident.Severity), incident.Summary))
		lines = append(lines, mutedStyle.Render(incident.Cause))
		lines = append(lines, warnStyle.Render("next: "+incident.Suggestion))
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
