package actions

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/envconfig"
	"github.com/kodoo/kodoo-tui/internal/event"
)

type row struct {
	header bool
	group  string
	action action
}

type action struct {
	Label             string
	Target            string
	Description       string
	RelevantKeys      []string
	RequireTypedCheck bool
	SelectDatabase    bool
	DatabaseBackend   string
}

// Model renders the actions tab.
type Model struct {
	cfg      *envconfig.Config
	width    int
	height   int
	rows     []row
	selected int
}

var (
	groupStyle    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("214"))
	actionStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))
	selectedStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	panelStyle    = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
)

// New builds the actions tab model.
func New(cfg *envconfig.Config) Model {
	rows := flattenRows([]struct {
		name    string
		actions []action
	}{
		{
			name: "Stacks",
			actions: []action{
				{Label: "Stable Docker · Public-Sector Runtime", Target: "up", Description: "Start the stable Docker stack with the public-sector runtime image.", RelevantKeys: []string{"DOMAIN", "PROD_DB_NAME", "OLLAMA_MODEL"}},
				{Label: "Stable Docker · Plain Runtime", Target: "up-base", Description: "Start the stable Docker stack with the plain Odoo runtime image.", RelevantKeys: []string{"DOMAIN", "PROD_DB_NAME", "OLLAMA_MODEL"}},
				{Label: "Public Tunnel", Target: "up-tunnel", Description: "Start the public Cloudflare-published stack.", RelevantKeys: []string{"DOMAIN", "CLOUDFLARED_TOKEN"}},
				{Label: "Local Nginx Stack", Target: "up-local", Description: "Start the local nginx-based stack.", RelevantKeys: []string{"LOCAL_BIND_HOST", "LOCAL_HTTP_PORT"}},
				{Label: "Insecure Test Stack", Target: "up-insecure", Description: "Expose Odoo ports directly for quick tests.", RelevantKeys: []string{"INSECURE_HTTP_PORT", "INSECURE_EVENTED_PORT"}},
				{Label: "Stop Active Docker Stack", Target: "down", Description: "Stop every compose service in the current stable stack.", RelevantKeys: []string{"DOMAIN"}, RequireTypedCheck: true},
				{Label: "Refresh Active Stable Stack", Target: "refresh-safe", Description: "Safely refresh the currently active stable Docker Odoo service.", RelevantKeys: []string{"PROD_DB_NAME", "PROD_DB_USER"}},
			},
		},
		{
			name: "Dev",
			actions: []action{
				{Label: "Client Dev · Docker DB", Target: "dev", Description: "Run native Odoo over Docker PostgreSQL after choosing a client database.", RelevantKeys: []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"}, SelectDatabase: true, DatabaseBackend: "docker"},
				{Label: "Client Dev · Local DB", Target: "dev-safe", Description: "Run native Odoo over local PostgreSQL after choosing a client database.", RelevantKeys: []string{"DEV_HOST_HTTP_PORT", "PG_LOCAL_PORT"}, SelectDatabase: true, DatabaseBackend: "local"},
				{Label: "Client Dev Alias · Docker DB", Target: "dev-project", Description: "Alias for shared Docker PostgreSQL project mode with client database selection.", RelevantKeys: []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"}, SelectDatabase: true, DatabaseBackend: "docker"},
				{Label: "Upgrade Local Client Modules", Target: "dev-host-upgrade", Description: "Upgrade selected modules in the local host mode.", RelevantKeys: []string{"DEV_UPGRADE_DB", "DEV_MODULES"}},
			},
		},
		{
			name: "Database",
			actions: []action{
				{Label: "Open Manager · Docker DB", Target: "db-init", Description: "Open the Odoo database manager against Docker PostgreSQL.", RelevantKeys: []string{"DEV_PROJECT_DB"}},
				{Label: "List Client Databases", Target: "db-list", Description: "List the available databases.", RelevantKeys: []string{"DEV_PROJECT_DB", "DEV_HOST_TEST_DB"}},
				{Label: "Backup Local Client DB", Target: "dev-host-backup", Description: "Create a local PostgreSQL backup.", RelevantKeys: []string{"DEV_HOST_DB", "BACKUP_DIR"}},
				{Label: "Restore Local ktest", Target: "dev-host-restore-ktest", Description: "Restore the latest backup into the local ktest database.", RelevantKeys: []string{"DEV_HOST_TEST_DB", "BACKUP_DIR"}, RequireTypedCheck: true},
			},
		},
		{
			name: "Health",
			actions: []action{
				{Label: "smoke", Target: "smoke", Description: "Run smoke checks.", RelevantKeys: []string{"DOMAIN", "LOCAL_HTTP_PORT"}},
				{Label: "troubleshoot", Target: "troubleshoot", Description: "Run the detailed diagnostics target.", RelevantKeys: []string{"DOMAIN"}},
				{Label: "doctor", Target: "doctor", Description: "Check host dependencies and prerequisites.", RelevantKeys: []string{"PG_LOCAL_SERVICE"}},
			},
		},
		{
			name: "Assets",
			actions: []action{
				{Label: "assets-rebuild", Target: "assets-rebuild", Description: "Rebuild web assets for the stable stack.", RelevantKeys: []string{"PROD_DB_NAME"}},
				{Label: "odoo-fix-url", Target: "odoo-fix-url", Description: "Force the Odoo base URL to the configured public domain.", RelevantKeys: []string{"DOMAIN", "PROD_DB_NAME"}},
			},
		},
		{
			name: "Mobile",
			actions: []action{
				{Label: "mobile-sync", Target: "mobile-sync", Description: "Sync Capacitor assets.", RelevantKeys: []string{"MOBILE_DIR"}},
				{Label: "mobile-open-android", Target: "mobile-open-android", Description: "Open the Android project.", RelevantKeys: []string{"MOBILE_DIR"}},
				{Label: "mobile-open-ios", Target: "mobile-open-ios", Description: "Open the iOS project.", RelevantKeys: []string{"MOBILE_DIR"}},
			},
		},
		{
			name: "Ollama",
			actions: []action{
				{Label: "ollama-pull", Target: "ollama-pull", Description: "Download the configured Ollama model.", RelevantKeys: []string{"OLLAMA_MODEL"}},
				{Label: "ollama-list", Target: "ollama-list", Description: "List local Ollama models.", RelevantKeys: []string{"OLLAMA_MODEL"}},
			},
		},
	})

	model := Model{cfg: cfg, rows: rows}
	model.selected = model.firstSelectable()
	return model
}

// Title returns the visible tab name.
func (m Model) Title() string {
	return "Actions"
}

// HelpLines returns the actions help text.
func (m Model) HelpLines() []string {
	return []string{
		"↑/↓  move between actions",
		"enter  confirm and execute the selected target",
		"destructive actions require typing 'sim'",
	}
}

// SetConfig updates the config pointer.
func (m Model) SetConfig(cfg *envconfig.Config) Model {
	m.cfg = cfg
	return m
}

// Init does not need a background command.
func (m Model) Init() tea.Cmd {
	return nil
}

// Update handles action navigation.
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
	case tea.KeyMsg:
		switch msg.String() {
		case "up":
			m.moveSelection(-1)
		case "down":
			m.moveSelection(1)
		case "enter":
			return m, requestCmd(m.request())
		}
	}
	return m, nil
}

// View renders the actions tab.
func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}

	listWidth := max(34, width/2)
	left := panelStyle.Width(listWidth).Height(max(10, height-4)).Render(m.actionsListView())
	right := panelStyle.Width(width-listWidth-4).Height(max(10, height-4)).Render(m.detailView())
	return lipgloss.JoinHorizontal(lipgloss.Top, left, right)
}

func (m Model) actionsListView() string {
	lines := []string{selectedStyle.Render("Actions")}
	for idx, row := range m.rows {
		if row.header {
			lines = append(lines, "", groupStyle.Render("▶ "+row.group))
			continue
		}
		style := actionStyle
		prefix := "    "
		if idx == m.selected {
			style = selectedStyle
			prefix = "  > "
		}
		lines = append(lines, style.Render(prefix+row.action.Label))
	}
	return strings.Join(lines, "\n")
}

func (m Model) detailView() string {
	action := m.currentAction()
	lines := []string{
		selectedStyle.Render("Selected Action"),
		fmt.Sprintf("target: %s", action.Target),
		action.Description,
		"",
		"Relevant variables:",
	}
	for _, key := range action.RelevantKeys {
		lines = append(lines, fmt.Sprintf("  %s=%s", key, m.cfg.MaskedValue(key)))
	}
	if action.RequireTypedCheck {
		lines = append(lines, "", "This action requires typed confirmation.")
	}
	return strings.Join(lines, "\n")
}

func (m Model) currentAction() action {
	if m.selected < 0 || m.selected >= len(m.rows) {
		return action{}
	}
	return m.rows[m.selected].action
}

func (m *Model) moveSelection(delta int) {
	if len(m.rows) == 0 {
		return
	}
	next := m.selected
	for {
		next += delta
		if next < 0 || next >= len(m.rows) {
			return
		}
		if !m.rows[next].header {
			m.selected = next
			return
		}
	}
}

func (m Model) firstSelectable() int {
	for idx, row := range m.rows {
		if !row.header {
			return idx
		}
	}
	return 0
}

func (m Model) request() tea.Msg {
	action := m.currentAction()
	return event.RequestMakeTargetMsg{
		Target:            action.Target,
		Description:       action.Description,
		RelevantKeys:      action.RelevantKeys,
		RequireTypedCheck: action.RequireTypedCheck,
		ConfirmWord:       "sim",
		SelectDatabase:    action.SelectDatabase,
		DatabaseBackend:   action.DatabaseBackend,
	}
}

func flattenRows(groups []struct {
	name    string
	actions []action
}) []row {
	rows := make([]row, 0, 64)
	for _, group := range groups {
		rows = append(rows, row{header: true, group: group.name})
		for _, action := range group.actions {
			rows = append(rows, row{action: action})
		}
	}
	return rows
}

func requestCmd(msg tea.Msg) tea.Cmd {
	return func() tea.Msg { return msg }
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
