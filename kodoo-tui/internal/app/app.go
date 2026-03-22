package app

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/database"
	"github.com/kodoo/kodoo-tui/internal/envconfig"
	"github.com/kodoo/kodoo-tui/internal/event"
	"github.com/kodoo/kodoo-tui/internal/runner"
	"github.com/kodoo/kodoo-tui/internal/ui/actions"
	"github.com/kodoo/kodoo-tui/internal/ui/config"
	"github.com/kodoo/kodoo-tui/internal/ui/dashboard"
	"github.com/kodoo/kodoo-tui/internal/ui/logs"
)

var (
	activeTabStyle   = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("16")).Background(lipgloss.Color("86")).Padding(0, 2)
	inactiveTabStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("252")).Background(lipgloss.Color("238")).Padding(0, 2)
	statusStyle      = lipgloss.NewStyle().Foreground(lipgloss.Color("252")).Background(lipgloss.Color("238")).Padding(0, 1)
	overlayStyle     = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	titleStyle       = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	successStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
	failureStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	warningStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	mutedStyle       = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
)

type overlayState struct {
	visible     bool
	request     *event.RequestMakeTargetMsg
	running     bool
	done        bool
	runnerID    string
	title       string
	description string
	lines       []string
	viewport    viewport.Model
	startedAt   time.Time
	statusText  string
	input       textinput.Model
	errorText   string
	selectingDB bool
	loadingDBs  bool
	databases   []database.Record
	selectedDB  int
}

type launchOption struct {
	Title       string
	Description string
	Request     event.RequestMakeTargetMsg
}

// Model is the root Bubble Tea application.
type Model struct {
	repoDir    string
	cfg        *envconfig.Config
	activeTab  int
	width      int
	height     int
	dashboard  dashboard.Model
	logs       logs.Model
	actions    actions.Model
	config     config.Model
	helpVisible bool
	launchpadVisible bool
	launchOptions    []launchOption
	launchSelected   int
	overlay    overlayState
	activeDB   string
}

// New creates the root kodoo-tui application.
func New(cfg *envconfig.Config, repoDir string) Model {
	input := textinput.New()
	input.Prompt = "type 'sim' > "
	input.CharLimit = 16
	input.Blur()

	return Model{
		repoDir:   repoDir,
		cfg:       cfg,
		dashboard: dashboard.New(cfg),
		logs:      logs.New(cfg),
		actions:   actions.New(cfg),
		config:    config.New(cfg),
		launchpadVisible: true,
		launchOptions:    defaultLaunchOptions(),
		overlay: overlayState{
			viewport: viewport.New(60, 10),
			input:    input,
		},
	}
}

// Init starts all tabs.
func (m Model) Init() tea.Cmd {
	return tea.Batch(
		m.dashboard.Init(),
		m.logs.Init(),
		m.actions.Init(),
		m.config.Init(),
	)
}

// Update handles the full application state.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.syncOverlayViewport()
		return m.updateAll(msg)
	case event.RequestMakeTargetMsg:
		return m.prepareActionRequest(msg)
	case database.MsgListLoaded:
		if !m.overlay.visible || !m.overlay.loadingDBs {
			return m, nil
		}
		m.overlay.loadingDBs = false
		if msg.Err != nil {
			m.overlay.done = true
			m.overlay.statusText = "database list failed"
			m.overlay.lines = []string{msg.Err.Error()}
			m.syncOverlayViewport()
			return m, nil
		}
		if len(msg.Databases) == 0 {
			m.overlay.done = true
			m.overlay.statusText = "no databases found"
			m.overlay.lines = []string{fmt.Sprintf("No %s databases are available for selection.", msg.Backend)}
			m.syncOverlayViewport()
			return m, nil
		}
		m.overlay.databases = msg.Databases
		m.overlay.selectedDB = 0
		return m, nil
	case event.RequestUpdateConfigMsg:
		m.cfg.Set(msg.Key, msg.Value)
		if err := m.cfg.Save(); err != nil {
			m.overlay.visible = true
			m.overlay.done = true
			m.overlay.title = "Config save"
			m.overlay.statusText = "save failed"
			m.overlay.lines = []string{err.Error()}
			m.syncOverlayViewport()
			return m, nil
		}
		return m.reloadConfig()
	case event.RequestOpenEditorMsg:
		return m, openEditor(msg.Path)
	case event.EditorDoneMsg:
		if msg.Err != nil {
			m.overlay.visible = true
			m.overlay.done = true
			m.overlay.running = false
			m.overlay.title = "Editor"
			m.overlay.statusText = "editor failed"
			m.overlay.lines = []string{msg.Err.Error()}
			m.syncOverlayViewport()
			return m, nil
		}
		return m.reloadConfig()
	case runner.MsgRunnerStarted:
		if m.overlay.visible {
			m.overlay.runnerID = msg.ID
			return m, runner.Next(msg.ID)
		}
	case runner.MsgOutputLine:
		if m.overlay.visible && msg.ID == m.overlay.runnerID {
			m.overlay.lines = append(m.overlay.lines, msg.Line)
			if len(m.overlay.lines) > 2000 {
				m.overlay.lines = m.overlay.lines[len(m.overlay.lines)-2000:]
			}
			m.syncOverlayViewport()
			return m, runner.Next(msg.ID)
		}
	case runner.MsgDone:
		if m.overlay.visible && msg.ID == m.overlay.runnerID {
			m.overlay.running = false
			m.overlay.done = true
			if msg.Err != nil {
				m.overlay.statusText = fmt.Sprintf("✗ failed with code %d", msg.ExitCode)
			} else {
				m.overlay.statusText = "✓ completed"
			}
			m.syncOverlayViewport()
			if msg.Err == nil {
				return m.reloadConfig()
			}
			return m, nil
		}
	case tea.KeyMsg:
		if handled, next, cmd := m.handleGlobalKey(msg); handled {
			return next, cmd
		}
		return m.updateActive(msg)
	}

	return m.updateAll(msg)
}

// View renders the complete TUI.
func (m Model) View() string {
	width := m.width
	height := m.height
	if width <= 0 {
		width = 120
	}
	if height <= 0 {
		height = 40
	}

	tabBar := m.tabsView()
	bodyHeight := height - 3
	mainHeight := bodyHeight
	overlayHeight := 0
	if m.overlay.visible || m.helpVisible || m.launchpadVisible {
		mainHeight = bodyHeight / 2
		overlayHeight = bodyHeight - mainHeight
	}

	content := m.activeTabView(width, max(10, mainHeight))
	parts := []string{tabBar, content}

	if m.helpVisible {
		parts = append(parts, m.helpView(width, max(8, overlayHeight)))
	} else if m.overlay.visible {
		parts = append(parts, m.overlayView(width, max(8, overlayHeight)))
	} else if m.launchpadVisible {
		parts = append(parts, m.launchpadView(width, max(8, overlayHeight)))
	}

	parts = append(parts, m.statusBar(width))
	return strings.Join(parts, "\n")
}

func (m Model) handleGlobalKey(msg tea.KeyMsg) (bool, Model, tea.Cmd) {
	switch msg.String() {
	case "ctrl+c", "q":
		return true, m, tea.Quit
	}

	if m.helpVisible {
		switch msg.String() {
		case "esc", "?":
			m.helpVisible = false
		}
		return true, m, nil
	}

	if m.overlay.visible {
		next, cmd := m.handleOverlayKey(msg)
		return true, next, cmd
	}

	if m.launchpadVisible {
		switch msg.String() {
		case "up":
			if m.launchSelected > 0 {
				m.launchSelected--
			}
		case "down":
			if m.launchSelected < len(m.launchOptions)-1 {
				m.launchSelected++
			}
		case "enter":
			m.launchpadVisible = false
			next, cmd := m.prepareActionRequest(m.launchOptions[m.launchSelected].Request)
			return true, next, cmd
		case "esc", "l":
			m.launchpadVisible = false
		}
		return true, m, nil
	}

	switch msg.String() {
	case "1":
		m.activeTab = 0
		return true, m, nil
	case "2":
		m.activeTab = 1
		return true, m, nil
	case "3":
		m.activeTab = 2
		return true, m, nil
	case "4":
		m.activeTab = 3
		return true, m, nil
	case "tab":
		m.activeTab = (m.activeTab + 1) % 4
		return true, m, nil
	case "shift+tab":
		m.activeTab = (m.activeTab + 3) % 4
		return true, m, nil
	case "?":
		m.helpVisible = true
		return true, m, nil
	case "l":
		m.launchpadVisible = true
		return true, m, nil
	}

	return false, m, nil
}

func (m Model) handleOverlayKey(msg tea.KeyMsg) (Model, tea.Cmd) {
	if m.overlay.running {
		return m, nil
	}

	if m.overlay.done {
		if msg.String() == "esc" || msg.String() == "enter" {
			m.overlay = m.newOverlay()
		}
		return m, nil
	}

	if msg.String() == "esc" {
		m.overlay = m.newOverlay()
		return m, nil
	}

	request := m.overlay.request
	if request == nil {
		return m, nil
	}

	if m.overlay.selectingDB {
		switch msg.String() {
		case "up":
			if m.overlay.selectedDB > 0 {
				m.overlay.selectedDB--
			}
		case "down":
			if m.overlay.selectedDB < len(m.overlay.databases)-1 {
				m.overlay.selectedDB++
			}
		case "enter":
			if len(m.overlay.databases) == 0 {
				return m, nil
			}
			if request.Vars == nil {
				request.Vars = make(map[string]string)
			}
			request.Vars["DB"] = m.overlay.databases[m.overlay.selectedDB].Name
			m.overlay.selectingDB = false
			m.overlay.errorText = ""
			if request.RequireTypedCheck {
				m.overlay.input.Focus()
			}
		}
		return m, nil
	}

	if request.RequireTypedCheck {
		var cmd tea.Cmd
		m.overlay.input, cmd = m.overlay.input.Update(msg)
		switch msg.String() {
		case "enter":
			if strings.EqualFold(strings.TrimSpace(m.overlay.input.Value()), request.ConfirmWord) {
				return m.startAction()
			}
			m.overlay.errorText = "Type 'sim' to confirm."
			return m, cmd
		}
		return m, cmd
	}

	if msg.String() == "enter" {
		return m.startAction()
	}

	return m, nil
}

func (m Model) startAction() (Model, tea.Cmd) {
	request := m.overlay.request
	if request == nil {
		return m, nil
	}

	m.overlay.running = true
	m.overlay.done = false
	m.overlay.startedAt = time.Now()
	m.overlay.statusText = "running..."
	m.overlay.lines = nil
	m.overlay.errorText = ""
	m.overlay.title = request.Target
	if selected := strings.TrimSpace(request.Vars["DB"]); selected != "" {
		m.activeDB = selected
	} else if clearsActiveDB(request.Target) {
		m.activeDB = ""
	}
	m.syncOverlayViewport()

	return m, runner.MakeTarget(context.Background(), m.repoDir, request.Target, request.Vars)
}

func (m Model) prepareActionRequest(request event.RequestMakeTargetMsg) (Model, tea.Cmd) {
	m.overlay = m.newOverlay()
	m.overlay.visible = true
	m.overlay.request = &request
	m.overlay.title = request.Target
	m.overlay.description = request.Description
	if request.SelectDatabase {
		m.overlay.selectingDB = true
		m.overlay.loadingDBs = true
		m.overlay.title = fmt.Sprintf("%s · select database", request.Target)
		return m, database.ListCmd(context.Background(), m.repoDir, request.DatabaseBackend)
	}
	if request.RequireTypedCheck {
		m.overlay.input.Focus()
	}
	m.syncOverlayViewport()
	return m, nil
}

func (m Model) reloadConfig() (Model, tea.Cmd) {
	cfg, err := envconfig.Load(filepath.Join(m.repoDir, ".env.make"))
	if err != nil {
		m.overlay.visible = true
		m.overlay.done = true
		m.overlay.title = "Config reload"
		m.overlay.statusText = "reload failed"
		m.overlay.lines = []string{err.Error()}
		m.syncOverlayViewport()
		return m, nil
	}

	m.cfg = cfg
	m.dashboard = m.dashboard.SetConfig(cfg)
	m.logs = m.logs.SetConfig(cfg)
	m.actions = m.actions.SetConfig(cfg)
	m.config = m.config.SetConfig(cfg)
	return m, nil
}

func (m Model) updateAll(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd
	var cmd tea.Cmd

	m.dashboard, cmd = m.dashboard.Update(msg)
	if cmd != nil {
		cmds = append(cmds, cmd)
	}
	m.logs, cmd = m.logs.Update(msg)
	if cmd != nil {
		cmds = append(cmds, cmd)
	}
	m.actions, cmd = m.actions.Update(msg)
	if cmd != nil {
		cmds = append(cmds, cmd)
	}
	m.config, cmd = m.config.Update(msg)
	if cmd != nil {
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

func (m Model) updateActive(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch m.activeTab {
	case 0:
		next, cmd := m.dashboard.Update(msg)
		m.dashboard = next
		return m, cmd
	case 1:
		next, cmd := m.logs.Update(msg)
		m.logs = next
		return m, cmd
	case 2:
		next, cmd := m.actions.Update(msg)
		m.actions = next
		return m, cmd
	default:
		next, cmd := m.config.Update(msg)
		m.config = next
		return m, cmd
	}
}

func (m Model) tabsView() string {
	tabs := []string{
		m.renderTab(0, "1 Dashboard"),
		m.renderTab(1, "2 Logs"),
		m.renderTab(2, "3 Actions"),
		m.renderTab(3, "4 Config"),
	}
	return lipgloss.JoinHorizontal(lipgloss.Top, tabs...)
}

func (m Model) renderTab(index int, label string) string {
	if index == m.activeTab {
		return activeTabStyle.Render(label)
	}
	return inactiveTabStyle.Render(label)
}

func (m Model) activeTabView(width, height int) string {
	switch m.activeTab {
	case 0:
		return m.dashboard.View(width, height)
	case 1:
		return m.logs.View(width, height)
	case 2:
		return m.actions.View(width, height)
	default:
		return m.config.View(width, height)
	}
}

func (m Model) helpView(width, height int) string {
	lines := []string{titleStyle.Render("Help")}
	lines = append(lines, m.currentHelpLines()...)
	lines = append(lines, "", "Global keys: 1-4 tabs · tab/shift+tab cycle · l launchpad · q quit · esc close overlay")
	return overlayStyle.Width(width - 2).Height(height - 1).Render(strings.Join(lines, "\n"))
}

func (m Model) overlayView(width, height int) string {
	lines := []string{
		titleStyle.Render(m.overlay.title),
	}

	if !m.overlay.running && !m.overlay.done && m.overlay.request != nil {
		if m.overlay.selectingDB {
			lines = append(lines, "Choose the client database for this action.")
			if m.overlay.loadingDBs {
				lines = append(lines, "", "Loading databases...")
			} else {
				lines = append(lines, "")
				lines = append(lines, m.databaseSelectionView()...)
				lines = append(lines, "", "Use ↑/↓ and press enter to continue.")
			}
			return overlayStyle.Width(width - 2).Height(height - 1).Render(strings.Join(lines, "\n"))
		}

		lines = append(lines, m.overlay.description)
		lines = append(lines, "", "Relevant variables:")
		for _, key := range m.overlay.request.RelevantKeys {
			lines = append(lines, fmt.Sprintf("  %s=%s", key, m.cfg.MaskedValue(key)))
		}
		if selected := strings.TrimSpace(m.overlay.request.Vars["DB"]); selected != "" {
			lines = append(lines, fmt.Sprintf("  DB=%s", selected))
		}
		if m.overlay.request.RequireTypedCheck {
			lines = append(lines, "", warningStyle.Render("Type 'sim' to confirm this destructive action."))
			if m.overlay.errorText != "" {
				lines = append(lines, failureStyle.Render(m.overlay.errorText))
			}
			lines = append(lines, m.overlay.input.View())
		} else {
			lines = append(lines, "", "Press enter to execute, esc to cancel.")
		}
		return overlayStyle.Width(width - 2).Height(height - 1).Render(strings.Join(lines, "\n"))
	}

	lines = append(lines, fmt.Sprintf("started: %s", m.overlay.startedAt.Format("15:04:05")))
	lines = append(lines, "", m.overlay.viewport.View(), "", m.overlay.statusText)
	if m.overlay.done {
		lines = append(lines, "Press esc to close.")
	}
	return overlayStyle.Width(width - 2).Height(height - 1).Render(strings.Join(lines, "\n"))
}

func (m Model) statusBar(width int) string {
	mode := m.dashboard.Mode()
	db := m.dbSummary(mode)
	bar := fmt.Sprintf("%s  |  mode: %s  |  db: %s  |  tab cycle · l launchpad · q quit · ? help",
		m.cfg.Domain,
		mode,
		db,
	)
	return statusStyle.Width(width).Render(bar)
}

func (m Model) dbSummary(mode string) string {
	switch mode {
	case "client dev · docker db":
		if m.activeDB != "" {
			return fmt.Sprintf("%s (docker pg :%d)", m.activeDB, m.cfg.DockerDBHostPort)
		}
		return fmt.Sprintf("database manager (docker pg :%d)", m.cfg.DockerDBHostPort)
	case "client dev · local db":
		if m.activeDB != "" {
			return fmt.Sprintf("%s (local pg :%d)", m.activeDB, m.cfg.PGLocalPort)
		}
		return fmt.Sprintf("database manager (local pg :%d)", m.cfg.PGLocalPort)
	default:
		return fmt.Sprintf("%s (docker pg :5432)", m.cfg.ProdDBName)
	}
}

func (m Model) currentHelpLines() []string {
	switch m.activeTab {
	case 0:
		return m.dashboard.HelpLines()
	case 1:
		return m.logs.HelpLines()
	case 2:
		return m.actions.HelpLines()
	default:
		return m.config.HelpLines()
	}
}

func (m *Model) syncOverlayViewport() {
	m.overlay.viewport.Width = max(20, m.width-8)
	m.overlay.viewport.Height = max(6, (m.height/2)-8)
	m.overlay.viewport.SetContent(strings.Join(m.overlay.lines, "\n"))
	m.overlay.viewport.GotoBottom()
}

func (m Model) newOverlay() overlayState {
	input := textinput.New()
	input.Prompt = "type 'sim' > "
	input.CharLimit = 16
	input.Blur()
	return overlayState{
		viewport: viewport.New(60, 10),
		input:    input,
	}
}

func (m Model) databaseSelectionView() []string {
	lines := []string{}
	for idx, record := range m.overlay.databases {
		prefix := "  "
		style := lipgloss.NewStyle()
		if idx == m.overlay.selectedDB {
			prefix = "> "
			style = successStyle.Bold(true)
		}
		label := fmt.Sprintf("%s (%s, %s, %s)", record.Name, record.Backend, record.Size, record.Tags)
		lines = append(lines, style.Render(prefix+label))
	}
	if len(lines) == 0 {
		lines = append(lines, "No databases available.")
	}
	return lines
}

func (m Model) launchpadView(width, height int) string {
	lines := []string{
		titleStyle.Render("Launchpad"),
		"Choose how you want to start Kodoo in this session.",
		"",
	}
	for idx, option := range m.launchOptions {
		prefix := "  "
		style := lipgloss.NewStyle()
		if idx == m.launchSelected {
			prefix = "> "
			style = successStyle.Bold(true)
		}
		lines = append(lines, style.Render(prefix+option.Title))
		lines = append(lines, mutedStyle.Render("    "+option.Description))
		lines = append(lines, "")
	}
	lines = append(lines, "Use ↑/↓ and press enter. Press esc to skip.")
	return overlayStyle.Width(width - 2).Height(height - 1).Render(strings.Join(lines, "\n"))
}

func defaultLaunchOptions() []launchOption {
	return []launchOption{
		{
			Title:       "Stable Docker · Public-Sector Runtime",
			Description: "Launch the stable Docker stack with the public-sector runtime.",
			Request: event.RequestMakeTargetMsg{
				Target:      "up",
				Description: "Start the stable Docker stack with the public-sector runtime.",
				RelevantKeys: []string{
					"DOMAIN", "PROD_DB_NAME", "OLLAMA_MODEL",
				},
			},
		},
		{
			Title:       "Stable Docker · Plain Runtime",
			Description: "Launch the stable Docker stack with the plain Odoo runtime image.",
			Request: event.RequestMakeTargetMsg{
				Target:      "up-base",
				Description: "Start the stable Docker stack with the plain Odoo runtime.",
				RelevantKeys: []string{
					"DOMAIN", "PROD_DB_NAME", "OLLAMA_MODEL",
				},
			},
		},
		{
			Title:       "Client Dev · Docker DB",
			Description: "Pick a client database and run native Odoo over Docker PostgreSQL.",
			Request: event.RequestMakeTargetMsg{
				Target:          "dev",
				Description:     "Run native Odoo over Docker PostgreSQL after choosing a client database.",
				RelevantKeys:    []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"},
				SelectDatabase:  true,
				DatabaseBackend: "docker",
			},
		},
		{
			Title:       "Client Dev · Local DB",
			Description: "Pick a client database and run native Odoo over local PostgreSQL.",
			Request: event.RequestMakeTargetMsg{
				Target:          "dev-safe",
				Description:     "Run native Odoo over local PostgreSQL after choosing a client database.",
				RelevantKeys:    []string{"DEV_HOST_HTTP_PORT", "PG_LOCAL_PORT"},
				SelectDatabase:  true,
				DatabaseBackend: "local",
			},
		},
		{
			Title:       "Database Manager · Docker DB",
			Description: "Open the database manager over Docker PostgreSQL without pinning a client DB.",
			Request: event.RequestMakeTargetMsg{
				Target:       "dev-project-up",
				Description:  "Open the database manager against Docker PostgreSQL.",
				RelevantKeys: []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"},
			},
		},
		{
			Title:       "Database Manager · Local DB",
			Description: "Open the database manager over local PostgreSQL without pinning a client DB.",
			Request: event.RequestMakeTargetMsg{
				Target:       "dev-host-up",
				Description:  "Open the database manager against local PostgreSQL.",
				RelevantKeys: []string{"DEV_HOST_HTTP_PORT", "PG_LOCAL_PORT"},
			},
		},
	}
}

func clearsActiveDB(target string) bool {
	switch target {
	case "dev", "dev-safe", "dev-project", "dev-project-up", "dev-host-up", "db-init":
		return true
	default:
		return false
	}
}

func openEditor(path string) tea.Cmd {
	editor := os.Getenv("EDITOR")
	if editor == "" {
		if _, err := exec.LookPath("nano"); err == nil {
			editor = "nano"
		} else {
			editor = "vi"
		}
	}

	command := exec.Command("sh", "-lc", fmt.Sprintf("%s %q", editor, path))
	return tea.ExecProcess(command, func(execErr error) tea.Msg {
		return event.EditorDoneMsg{Path: path, Err: execErr}
	})
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
