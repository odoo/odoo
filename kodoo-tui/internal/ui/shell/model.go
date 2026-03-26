package shell

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/event"
	"github.com/kodoo/kodoo-tui/internal/state"
)

type Model struct {
	snapshot state.Snapshot
}

var (
	titleStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	panelStyle = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	mutedStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
	okStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
	warnStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
)

func New() Model {
	return Model{}
}

func (m Model) Title() string {
	return "Shell"
}

func (m Model) HelpLines() []string {
	return []string{
		"enter open the contextual Odoo shell",
		"s choose a database before opening the shell",
		"r refresh the global snapshot",
	}
}

func (m Model) Init() tea.Cmd {
	return nil
}

func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "enter":
			return m, requestCmd(BuildContextualShellRequest(m.snapshot, false))
		case "s":
			return m, requestCmd(BuildContextualShellRequest(m.snapshot, true))
		}
	}
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

	leftWidth := max(38, width/2)
	rightWidth := max(30, width-leftWidth-4)
	left := panelStyle.Width(leftWidth).Height(max(10, height-4)).Render(m.summaryView())
	right := panelStyle.Width(rightWidth).Height(max(10, height-4)).Render(m.actionView())
	return lipgloss.JoinHorizontal(lipgloss.Top, left, right)
}

func (m Model) summaryView() string {
	request := BuildContextualShellRequest(m.snapshot, false)
	dbLabel := fallbackDB(m.snapshot)
	lines := []string{
		titleStyle.Render("Contextual Odoo Shell"),
		mutedStyle.Render("Interactive shell bound to the active runtime mode."),
		"",
		fmt.Sprintf("mode: %s", fallback(m.snapshot.Runtime.Mode, "Stopped")),
		fmt.Sprintf("backend: %s", backendLabel(request)),
		fmt.Sprintf("target: make %s", request.Target),
		fmt.Sprintf("database: %s", dbLabel),
		fmt.Sprintf("runtime db backend: %s", fallback(m.snapshot.Runtime.DBBackend, "unknown")),
	}

	if dbLabel == "select on open" {
		lines = append(lines, warnStyle.Render("No database pinned in the TUI. Press enter or s to choose one."))
	} else {
		lines = append(lines, okStyle.Render("The shell will open directly on the pinned database."))
	}

	lines = append(lines, "", titleStyle.Render("Command Preview"))
	lines = append(lines, previewCommand(request))
	return strings.Join(lines, "\n")
}

func (m Model) actionView() string {
	request := BuildContextualShellRequest(m.snapshot, false)
	lines := []string{
		titleStyle.Render("Actions"),
		"enter",
		"Open the contextual Odoo shell now.",
		"",
		"s",
		"Force database selection before opening the shell.",
		"",
		titleStyle.Render("Operational Notes"),
		noteForMode(m.snapshot.Runtime.Mode),
		"",
		titleStyle.Render("Selected Flow"),
		request.Description,
	}
	return strings.Join(lines, "\n")
}

func BuildContextualShellRequest(snapshot state.Snapshot, forceSelect bool) event.RequestMakeTargetMsg {
	mode := snapshot.Runtime.Mode
	request := event.RequestMakeTargetMsg{
		Interactive: true,
	}

	switch mode {
	case "Dev Host":
		request.Target = "dev-host-shell"
		request.Description = "Open the native Odoo shell against the local PostgreSQL database."
		request.DatabaseBackend = "local"
	case "Dev Project":
		request.Target = "dev-project-shell"
		request.Description = "Open the native Odoo shell against the Docker-backed development database."
		request.DatabaseBackend = "docker"
	case "Stable Tunnel", "Stable Docker", "Stopped", "":
		request.Target = "odoo-shell"
		request.Description = "Open the Odoo shell inside the stable Docker runtime container."
		request.DatabaseBackend = "docker"
	default:
		request.Target = "odoo-shell"
		request.Description = "Open the Odoo shell for the current stack."
		request.DatabaseBackend = "docker"
	}

	request.RelevantKeys = []string{"DOMAIN"}
	if request.DatabaseBackend == "local" {
		request.RelevantKeys = append(request.RelevantKeys, "PG_LOCAL_PORT")
	} else {
		request.RelevantKeys = append(request.RelevantKeys, "DOCKER_DB_HOST_PORT")
	}

	if !forceSelect && strings.TrimSpace(snapshot.Runtime.ActiveDB) != "" {
		request.Vars = map[string]string{"DB": strings.TrimSpace(snapshot.Runtime.ActiveDB)}
	} else {
		request.SelectDatabase = true
	}

	return request
}

func requestCmd(req event.RequestMakeTargetMsg) tea.Cmd {
	return func() tea.Msg { return req }
}

func previewCommand(request event.RequestMakeTargetMsg) string {
	db := "$(choose DB)"
	if request.Vars != nil && strings.TrimSpace(request.Vars["DB"]) != "" {
		db = request.Vars["DB"]
	}
	return fmt.Sprintf("make DB=%s %s", db, request.Target)
}

func backendLabel(request event.RequestMakeTargetMsg) string {
	if request.DatabaseBackend == "local" {
		return "native Odoo + local PostgreSQL"
	}
	return "Docker Odoo runtime"
}

func fallbackDB(snapshot state.Snapshot) string {
	if strings.TrimSpace(snapshot.Runtime.ActiveDB) != "" {
		return snapshot.Runtime.ActiveDB
	}
	return "select on open"
}

func noteForMode(mode string) string {
	switch mode {
	case "Dev Host":
		return "Uses the host Python runtime and the local PostgreSQL service."
	case "Dev Project":
		return "Uses the host Python runtime with the project Docker PostgreSQL bind."
	case "Stable Docker", "Stable Tunnel":
		return "Executes inside the running Odoo container of the stable stack."
	case "Stopped", "":
		return "No runtime is marked active. The shell target will use the stable Docker context."
	default:
		return "Shell resolution falls back to the stable Docker target for unknown modes."
	}
}

func fallback(value, defaultValue string) string {
	if strings.TrimSpace(value) == "" {
		return defaultValue
	}
	return value
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
