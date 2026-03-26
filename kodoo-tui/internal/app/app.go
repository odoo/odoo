package app

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
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
	"github.com/kodoo/kodoo-tui/internal/state"
	"github.com/kodoo/kodoo-tui/internal/ui/config"
	"github.com/kodoo/kodoo-tui/internal/ui/dashboard"
	"github.com/kodoo/kodoo-tui/internal/ui/databases"
	"github.com/kodoo/kodoo-tui/internal/ui/doctor"
	"github.com/kodoo/kodoo-tui/internal/ui/logs"
	"github.com/kodoo/kodoo-tui/internal/ui/runtime"
)

var (
	activeTabStyle   = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("16")).Background(lipgloss.Color("86")).Padding(0, 2)
	inactiveTabStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("252")).Background(lipgloss.Color("238")).Padding(0, 2)
	statusStyle      = lipgloss.NewStyle().Foreground(lipgloss.Color("252")).Background(lipgloss.Color("238")).Padding(0, 1)
	overlayStyle     = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	titleStyle       = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	failureStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	warningStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	mutedStyle       = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
)

type overlayState struct {
	visible      bool
	request      *event.RequestMakeTargetMsg
	running      bool
	done         bool
	runnerID     string
	title        string
	description  string
	lines        []string
	viewport     viewport.Model
	startedAt    time.Time
	statusText   string
	input        textinput.Model
	promptInput  textinput.Model
	promptIndex  int
	promptValues map[string]string
	errorText    string
	selectingDB  bool
	loadingDBs   bool
	databases    []database.Record
	selectedDB   int
	sessionIndex int
	autoFollow   bool
}

type actionRun struct {
	Title       string
	Description string
	StartedAt   time.Time
	FinishedAt  time.Time
	StatusText  string
	Lines       []string
	SavedPath   string
}

type overlaySavedMsg struct {
	path string
	err  error
}

type paletteMode int

const (
	paletteSwitch paletteMode = iota
	paletteAction
)

type paletteOption struct {
	Title       string
	Description string
	Mode        paletteMode
	Tab         int
	Request     event.RequestMakeTargetMsg
}

type tickMsg time.Time

type Model struct {
	repoDir        string
	cfg            *envconfig.Config
	activeTab      int
	width          int
	height         int
	snapshot       state.Snapshot
	dashboard      dashboard.Model
	runtime        runtime.Model
	databases      databases.Model
	doctor         doctor.Model
	logs           logs.Model
	config         config.Model
	helpVisible    bool
	paletteVisible bool
	palette        []paletteOption
	paletteIndex   int
	overlay        overlayState
	sessionRuns    []actionRun
	activeDB       string
	lastError      string
}

func New(cfg *envconfig.Config, repoDir string) Model {
	input := textinput.New()
	input.Prompt = "type 'sim' > "
	input.CharLimit = 16
	input.Blur()

	model := Model{
		repoDir:   repoDir,
		cfg:       cfg,
		dashboard: dashboard.New(cfg),
		runtime:   runtime.New(),
		databases: databases.New(cfg),
		doctor:    doctor.New(),
		logs:      logs.New().SetTailLines(cfg.TUILogLines),
		config:    config.New(cfg),
		overlay: overlayState{
			viewport: viewport.New(60, 10),
			input:    input,
		},
	}
	model.palette = model.buildPalette()
	return model
}

func (m Model) Init() tea.Cmd {
	return tea.Batch(
		state.RefreshCmd(m.cfg, m.repoDir, m.activeDB),
		tickCmd(m.cfg.RefreshInterval()),
		m.logs.Init(),
	)
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.syncOverlayViewport()
		return m.updateAll(msg)
	case tickMsg:
		return m, tea.Batch(state.RefreshCmd(m.cfg, m.repoDir, m.activeDB), tickCmd(m.cfg.RefreshInterval()))
	case state.MsgSnapshotLoaded:
		if msg.Err != nil {
			m.lastError = msg.Err.Error()
			return m, nil
		}
		m.lastError = ""
		m.snapshot = msg.Snapshot
		m.dashboard = m.dashboard.SetSnapshot(msg.Snapshot)
		m.runtime = m.runtime.SetSnapshot(msg.Snapshot)
		m.databases = m.databases.SetSnapshot(msg.Snapshot)
		m.doctor = m.doctor.SetSnapshot(msg.Snapshot)
		m.logs = m.logs.SetSnapshot(msg.Snapshot)
		m.config = m.config.SetSnapshot(msg.Snapshot)
		m.databases = m.databases.SetConfig(m.cfg)
		m.palette = m.buildPalette()
		return m, nil
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
			if m.overlay.sessionIndex >= 0 && m.overlay.sessionIndex < len(m.sessionRuns) {
				m.sessionRuns[m.overlay.sessionIndex].Lines = append(m.sessionRuns[m.overlay.sessionIndex].Lines, msg.Line)
			}
			m.syncOverlayViewport()
			return m, runner.Next(msg.ID)
		}
	case runner.MsgDone:
		if m.overlay.visible && msg.ID == m.overlay.runnerID {
			m.overlay.running = false
			m.overlay.done = true
			if msg.Err != nil {
				m.overlay.statusText = fmt.Sprintf("failed with code %d", msg.ExitCode)
				if summary := summarizeRunFailure(m.overlay.request, m.overlay.lines); summary != "" {
					m.overlay.lines = append([]string{"Summary: " + summary, ""}, m.overlay.lines...)
				}
			} else {
				m.overlay.statusText = "completed"
				if summary := summarizeRunSuccess(m.overlay.request, m.overlay.lines); summary != "" {
					m.overlay.lines = append([]string{"Summary: " + summary, ""}, m.overlay.lines...)
				}
			}
			if m.overlay.sessionIndex >= 0 && m.overlay.sessionIndex < len(m.sessionRuns) {
				m.sessionRuns[m.overlay.sessionIndex].StatusText = m.overlay.statusText
				m.sessionRuns[m.overlay.sessionIndex].FinishedAt = time.Now()
			}
			m.syncOverlayViewport()
			return m, tea.Batch(state.RefreshCmd(m.cfg, m.repoDir, m.activeDB))
		}
	case overlaySavedMsg:
		if msg.err != nil {
			m.overlay.statusText = "save failed"
			m.overlay.lines = append(m.overlay.lines, "save error: "+msg.err.Error())
		} else {
			m.overlay.statusText = "saved to " + msg.path
			if m.overlay.sessionIndex >= 0 && m.overlay.sessionIndex < len(m.sessionRuns) {
				m.sessionRuns[m.overlay.sessionIndex].SavedPath = msg.path
			}
		}
		m.syncOverlayViewport()
		return m, nil
	case tea.KeyMsg:
		if handled, next, cmd := m.handleGlobalKey(msg); handled {
			return next, cmd
		}
		return m.updateActive(msg)
	}

	return m.updateAll(msg)
}

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
	if m.overlay.visible || m.helpVisible || m.paletteVisible {
		mainHeight = bodyHeight / 2
		overlayHeight = bodyHeight - mainHeight
	}

	content := m.activeTabView(width, max(10, mainHeight))
	parts := []string{tabBar, content}

	if m.helpVisible {
		parts = append(parts, m.helpView(width, max(8, overlayHeight)))
	} else if m.overlay.visible {
		parts = append(parts, m.overlayView(width, max(8, overlayHeight)))
	} else if m.paletteVisible {
		parts = append(parts, m.paletteView(width, max(8, overlayHeight)))
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

	if m.paletteVisible {
		switch msg.String() {
		case "up":
			if m.paletteIndex > 0 {
				m.paletteIndex--
			}
		case "down":
			if m.paletteIndex < len(m.palette)-1 {
				m.paletteIndex++
			}
		case "enter":
			selected := m.palette[m.paletteIndex]
			m.paletteVisible = false
			if selected.Mode == paletteSwitch {
				m.activeTab = selected.Tab
				return true, m, nil
			}
			next, cmd := m.prepareActionRequest(selected.Request)
			return true, next, cmd
		case "esc", "ctrl+p":
			m.paletteVisible = false
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
	case "5":
		m.activeTab = 4
		return true, m, nil
	case "6":
		m.activeTab = 5
		return true, m, nil
	case "tab":
		m.activeTab = (m.activeTab + 1) % 6
		return true, m, nil
	case "shift+tab":
		m.activeTab = (m.activeTab + 5) % 6
		return true, m, nil
	case "?":
		m.helpVisible = true
		return true, m, nil
	case "ctrl+p":
		m.paletteVisible = true
		m.palette = m.buildPalette()
		m.paletteIndex = 0
		return true, m, nil
	case "ctrl+y":
		if len(m.sessionRuns) > 0 {
			m = m.openSessionRun(len(m.sessionRuns) - 1)
		}
		return true, m, nil
	case "ctrl+r":
		return true, m, state.RefreshCmd(m.cfg, m.repoDir, m.activeDB)
	}

	if m.activeTab == 0 {
		switch msg.String() {
		case "w":
			m.activeTab = 1
			return true, m, nil
		case "d":
			m.activeTab = 2
			return true, m, nil
		case "l":
			m.activeTab = 4
			return true, m, nil
		case "c":
			m.activeTab = 5
			return true, m, nil
		case "t":
			next, cmd := m.prepareActionRequest(event.RequestMakeTargetMsg{
				Target:      "troubleshoot",
				Description: "Run the detailed diagnostics target.",
				RelevantKeys: []string{
					"DOMAIN",
				},
			})
			return true, next, cmd
		case "s":
			next, cmd := m.prepareActionRequest(m.contextualStartStop())
			return true, next, cmd
		}
	}

	return false, m, nil
}

func (m Model) handleOverlayKey(msg tea.KeyMsg) (Model, tea.Cmd) {
	if m.overlay.running {
		if handled, next, cmd := m.handleOverlayViewportKey(msg); handled {
			return next, cmd
		}
		return m, nil
	}

	if m.overlay.done {
		if handled, next, cmd := m.handleOverlayViewportKey(msg); handled {
			return next, cmd
		}
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
			if len(request.PromptFields) > 0 {
				if m.overlay.promptValues == nil {
					m.overlay.promptValues = make(map[string]string, len(request.PromptFields))
				}
				m = m.preparePromptStep()
			} else if request.RequireTypedCheck {
				m.overlay.input.Focus()
			}
		}
		return m, nil
	}

	if m.overlay.prompting() {
		var cmd tea.Cmd
		m.overlay.promptInput, cmd = m.overlay.promptInput.Update(msg)
		switch msg.String() {
		case "enter":
			value := strings.TrimSpace(m.overlay.promptInput.Value())
			if value == "" {
				m.overlay.errorText = "This value is required."
				return m, cmd
			}
			field := request.PromptFields[m.overlay.promptIndex]
			if request.Vars == nil {
				request.Vars = make(map[string]string)
			}
			request.Vars[field.Key] = value
			m.overlay.promptValues[field.Key] = value
			m.overlay.promptIndex++
			m.overlay.errorText = ""
			if m.overlay.prompting() {
				m = m.preparePromptStep()
				return m, nil
			}
			m.overlay.promptInput.Blur()
			if request.RequireTypedCheck {
				m.overlay.input.Focus()
			}
		}
		return m, cmd
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
	m.overlay.autoFollow = true
	m.overlay.sessionIndex = len(m.sessionRuns)
	m.sessionRuns = append(m.sessionRuns, actionRun{
		Title:       request.Target,
		Description: request.Description,
		StartedAt:   m.overlay.startedAt,
		StatusText:  m.overlay.statusText,
	})
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
	if len(request.PromptFields) > 0 {
		m.overlay.promptValues = make(map[string]string, len(request.PromptFields))
		m = m.preparePromptStep()
	}
	if request.RequireTypedCheck {
		m.overlay.input.Focus()
	}
	m.syncOverlayViewport()
	return m, nil
}

func (m Model) reloadConfig() (Model, tea.Cmd) {
	cfg, err := envconfig.Load(envconfig.ResolvePath(m.repoDir))
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
	m.logs = logs.New().SetTailLines(cfg.TUILogLines).SetSnapshot(m.snapshot)
	m.dashboard = m.dashboard.SetConfig(cfg)
	m.databases = m.databases.SetConfig(cfg)
	m.config = m.config.SetConfig(cfg)
	m.palette = m.buildPalette()
	return m, state.RefreshCmd(m.cfg, m.repoDir, m.activeDB)
}

func (m Model) updateAll(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd
	var cmd tea.Cmd

	m.dashboard, cmd = m.dashboard.Update(msg)
	if cmd != nil {
		cmds = append(cmds, cmd)
	}
	m.runtime, cmd = m.runtime.Update(msg)
	if cmd != nil {
		cmds = append(cmds, cmd)
	}
	m.databases, cmd = m.databases.Update(msg)
	if cmd != nil {
		cmds = append(cmds, cmd)
	}
	m.doctor, cmd = m.doctor.Update(msg)
	if cmd != nil {
		cmds = append(cmds, cmd)
	}
	m.logs, cmd = m.logs.Update(msg)
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
		next, cmd := m.runtime.Update(msg)
		m.runtime = next
		return m, cmd
	case 2:
		next, cmd := m.databases.Update(msg)
		m.databases = next
		return m, cmd
	case 3:
		next, cmd := m.doctor.Update(msg)
		m.doctor = next
		return m, cmd
	case 4:
		next, cmd := m.logs.Update(msg)
		m.logs = next
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
		m.renderTab(1, "2 Runtime"),
		m.renderTab(2, "3 Databases"),
		m.renderTab(3, "4 Doctor"),
		m.renderTab(4, "5 Logs"),
		m.renderTab(5, "6 Config"),
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
		return m.runtime.View(width, height)
	case 2:
		return m.databases.View(width, height)
	case 3:
		return m.doctor.View(width, height)
	case 4:
		return m.logs.View(width, height)
	default:
		return m.config.View(width, height)
	}
}

func (m Model) helpView(width, height int) string {
	lines := []string{titleStyle.Render("Help")}
	lines = append(lines, m.currentHelpLines()...)
	lines = append(lines, "", "Global keys: 1-6 tabs · tab/shift+tab cycle · ctrl+p palette · ctrl+r refresh · ctrl+y last run · q quit · esc close overlay")
	return overlayStyle.Width(width - 2).Height(height - 1).Render(strings.Join(lines, "\n"))
}

func (m Model) overlayView(width, height int) string {
	lines := []string{titleStyle.Render(m.overlay.title)}

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

		if m.overlay.prompting() {
			field := m.overlay.request.PromptFields[m.overlay.promptIndex]
			lines = append(lines, m.overlay.description)
			lines = append(lines, "", "Relevant variables:")
			for _, key := range m.overlay.request.RelevantKeys {
				lines = append(lines, fmt.Sprintf("  %s=%s", key, m.cfg.MaskedValue(key)))
			}
			if selected := strings.TrimSpace(m.overlay.request.Vars["DB"]); selected != "" {
				lines = append(lines, fmt.Sprintf("  DB=%s", selected))
			}
			lines = append(lines, "")
			lines = append(lines, titleStyle.Render(fmt.Sprintf("Prompt %d/%d", m.overlay.promptIndex+1, len(m.overlay.request.PromptFields))))
			lines = append(lines, field.Label)
			if field.Placeholder != "" {
				lines = append(lines, mutedStyle.Render("  "+field.Placeholder))
			}
			if m.overlay.errorText != "" {
				lines = append(lines, failureStyle.Render(m.overlay.errorText))
			}
			lines = append(lines, m.overlay.promptInput.View())
			lines = append(lines, "", "Press enter to continue, esc to cancel.")
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
	if m.overlay.sessionIndex >= 0 && m.overlay.sessionIndex < len(m.sessionRuns) {
		run := m.sessionRuns[m.overlay.sessionIndex]
		if run.SavedPath != "" {
			lines = append(lines, "saved: "+run.SavedPath)
		}
	}
	lines = append(lines, "keys: ↑/↓ scroll  pgup/pgdn page  g top  G end/follow  w save")
	lines = append(lines, "", m.overlay.viewport.View(), "", m.overlay.statusText)
	if m.overlay.done {
		lines = append(lines, "Press esc to close.")
	}
	return overlayStyle.Width(width - 2).Height(height - 1).Render(strings.Join(lines, "\n"))
}

func (m Model) paletteView(width, height int) string {
	lines := []string{
		titleStyle.Render("Command Palette"),
		"Quick switcher for screens, runtime actions and diagnostics.",
	}
	for idx, item := range m.palette {
		style := lipgloss.NewStyle()
		prefix := "  "
		if idx == m.paletteIndex {
			style = titleStyle
			prefix = "> "
		}
		lines = append(lines, "", style.Render(prefix+item.Title))
		lines = append(lines, mutedStyle.Render(item.Description))
	}
	return overlayStyle.Width(width - 2).Height(height - 1).Render(strings.Join(lines, "\n"))
}

func (m Model) statusBar(width int) string {
	mode := m.snapshot.Runtime.Mode
	if mode == "" {
		mode = "loading"
	}
	db := m.activeDB
	if db == "" {
		db = "not pinned"
	}
	incident := m.snapshot.Runtime.LastIncident
	if incident == "" {
		incident = "no incidents"
	}
	if m.lastError != "" {
		incident = m.lastError
	}
	bar := fmt.Sprintf("%s  |  mode: %s  |  db: %s  |  incident: %s  |  ctrl+p palette · ctrl+y last run · ctrl+r refresh · q quit · ? help",
		m.cfg.Domain, mode, db, incident,
	)
	return statusStyle.Width(width).Render(bar)
}

func (m Model) currentHelpLines() []string {
	switch m.activeTab {
	case 0:
		return m.dashboard.HelpLines()
	case 1:
		return m.runtime.HelpLines()
	case 2:
		return m.databases.HelpLines()
	case 3:
		return m.doctor.HelpLines()
	case 4:
		return m.logs.HelpLines()
	default:
		return m.config.HelpLines()
	}
}

func (m *Model) syncOverlayViewport() {
	offset := m.overlay.viewport.YOffset
	m.overlay.viewport.Width = max(20, m.width-8)
	m.overlay.viewport.Height = max(6, (m.height/2)-8)
	m.overlay.viewport.SetContent(strings.Join(m.overlay.lines, "\n"))
	if m.overlay.autoFollow {
		m.overlay.viewport.GotoBottom()
		return
	}
	m.overlay.viewport.YOffset = offset
}

func (m Model) databaseSelectionView() []string {
	lines := make([]string, 0, len(m.overlay.databases))
	for idx, item := range m.overlay.databases {
		style := lipgloss.NewStyle()
		prefix := "  "
		if idx == m.overlay.selectedDB {
			style = titleStyle
			prefix = "> "
		}
		lines = append(lines, style.Render(fmt.Sprintf("%s%s (%s · %s)", prefix, item.Name, item.Owner, item.Size)))
	}
	return lines
}

func (m Model) newOverlay() overlayState {
	input := textinput.New()
	input.Prompt = "type 'sim' > "
	input.CharLimit = 16
	input.Blur()
	promptInput := textinput.New()
	promptInput.Prompt = "> "
	promptInput.CharLimit = 128
	promptInput.Blur()
	return overlayState{
		viewport:     viewport.New(60, 10),
		input:        input,
		promptInput:  promptInput,
		promptValues: make(map[string]string),
		sessionIndex: -1,
		autoFollow:   true,
	}
}

func (m overlayState) prompting() bool {
	return m.request != nil && m.promptIndex < len(m.request.PromptFields)
}

func (m Model) preparePromptStep() Model {
	if !m.overlay.prompting() {
		return m
	}
	field := m.overlay.request.PromptFields[m.overlay.promptIndex]
	input := textinput.New()
	input.Prompt = "> "
	input.Placeholder = field.Placeholder
	input.CharLimit = 128
	if field.Secret {
		input.EchoMode = textinput.EchoPassword
		input.EchoCharacter = '*'
	}
	input.Focus()
	m.overlay.promptInput = input
	return m
}

func (m Model) openSessionRun(index int) Model {
	if index < 0 || index >= len(m.sessionRuns) {
		return m
	}
	run := m.sessionRuns[index]
	m.overlay = m.newOverlay()
	m.overlay.visible = true
	m.overlay.done = true
	m.overlay.title = run.Title
	m.overlay.description = run.Description
	m.overlay.startedAt = run.StartedAt
	m.overlay.statusText = run.StatusText
	m.overlay.lines = append([]string(nil), run.Lines...)
	m.overlay.sessionIndex = index
	m.overlay.autoFollow = false
	m.syncOverlayViewport()
	return m
}

func (m Model) handleOverlayViewportKey(msg tea.KeyMsg) (bool, Model, tea.Cmd) {
	switch msg.String() {
	case "up":
		m.overlay.autoFollow = false
		m.overlay.viewport.LineUp(1)
		return true, m, nil
	case "down":
		m.overlay.autoFollow = false
		m.overlay.viewport.LineDown(1)
		return true, m, nil
	case "pgup":
		m.overlay.autoFollow = false
		m.overlay.viewport.HalfViewUp()
		return true, m, nil
	case "pgdown":
		m.overlay.autoFollow = false
		m.overlay.viewport.HalfViewDown()
		return true, m, nil
	case "g", "home":
		m.overlay.autoFollow = false
		m.overlay.viewport.GotoTop()
		return true, m, nil
	case "G", "end":
		m.overlay.autoFollow = true
		m.overlay.viewport.GotoBottom()
		return true, m, nil
	case "w":
		run, ok := m.currentSessionRun()
		if !ok {
			return true, m, nil
		}
		m.overlay.statusText = "saving..."
		return true, m, saveSessionRunCmd(m.repoDir, run)
	default:
		return false, m, nil
	}
}

func (m Model) currentSessionRun() (actionRun, bool) {
	if m.overlay.sessionIndex < 0 || m.overlay.sessionIndex >= len(m.sessionRuns) {
		return actionRun{}, false
	}
	return m.sessionRuns[m.overlay.sessionIndex], true
}

func saveSessionRunCmd(repoDir string, run actionRun) tea.Cmd {
	return func() tea.Msg {
		dir := filepath.Join(repoDir, "logs", "tui-session")
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return overlaySavedMsg{err: err}
		}
		name := fmt.Sprintf("%s_%s.log", run.StartedAt.Format("20060102_150405"), slugify(run.Title))
		path := filepath.Join(dir, name)
		var body []string
		body = append(body, "title: "+run.Title)
		body = append(body, "started: "+run.StartedAt.Format(time.RFC3339))
		if !run.FinishedAt.IsZero() {
			body = append(body, "finished: "+run.FinishedAt.Format(time.RFC3339))
		}
		body = append(body, "status: "+run.StatusText)
		if strings.TrimSpace(run.Description) != "" {
			body = append(body, "description: "+run.Description)
		}
		body = append(body, "", strings.Join(run.Lines, "\n"))
		if err := os.WriteFile(path, []byte(strings.Join(body, "\n")+"\n"), 0o644); err != nil {
			return overlaySavedMsg{err: err}
		}
		return overlaySavedMsg{path: path}
	}
}

var slugPattern = regexp.MustCompile(`[^a-z0-9]+`)

func slugify(value string) string {
	slug := strings.ToLower(strings.TrimSpace(value))
	slug = slugPattern.ReplaceAllString(slug, "-")
	slug = strings.Trim(slug, "-")
	if slug == "" {
		return "run"
	}
	return slug
}

func summarizeRunFailure(request *event.RequestMakeTargetMsg, lines []string) string {
	body := strings.ToLower(strings.Join(lines, "\n"))
	switch {
	case strings.Contains(body, "address already in use"), strings.Contains(body, "errno 98"):
		return "Port already in use. The helper tried to start an HTTP service while the stack was already bound."
	case strings.Contains(body, "user not found:"):
		for _, line := range lines {
			if strings.Contains(strings.ToLower(line), "user not found:") {
				return strings.TrimSpace(line)
			}
		}
		return "User login not found in the selected database."
	case strings.Contains(body, "refusing tenant-reset for primary db"), strings.Contains(body, "refusing reset of primary db"):
		return "Primary database reset is blocked."
	case strings.Contains(body, "could not resolve host"), request != nil && request.Target == "root-smoke":
		return "Public apex hostname is not resolving. Publish the apex domain in Cloudflare."
	case strings.Contains(body, "www resolves, but apex"), strings.Contains(body, "apex dns"):
		return "WWW resolves, but the apex domain is still missing on the edge."
	case strings.Contains(body, "this value is required"):
		return "A required prompt value was left empty."
	default:
		return ""
	}
}

func summarizeRunSuccess(request *event.RequestMakeTargetMsg, lines []string) string {
	if request == nil {
		return ""
	}
	switch request.Target {
	case "tenant-user-password":
		if line := findLineContains(lines, "password updated for "); line != "" {
			return line
		}
	case "tenant-user-role":
		if line := findLineContains(lines, "user role updated for "); line != "" {
			return line
		}
	case "tenant-user-create-portal":
		if line := findLineContains(lines, "portal user created for "); line != "" {
			return line
		}
	case "tenant-bootstrap-defaults":
		if line := findLineContains(lines, "tenant defaults applied to "); line != "" {
			return line
		}
	case "tenant-reset":
		if line := findLineContains(lines, "Tenant database '"); line != "" {
			return line
		}
	case "tenant-user-list":
		if count := countUserRows(lines); count > 0 {
			return fmt.Sprintf("%d tenant users listed.", count)
		}
	case "root-smoke":
		if line := findLineContains(lines, "OK: public root https://"); line != "" {
			return line
		}
		if line := findLineContains(lines, "OK: local root host "); line != "" {
			return line
		}
	}
	return ""
}

func findLineContains(lines []string, pattern string) string {
	for _, line := range lines {
		if strings.Contains(line, pattern) {
			return strings.TrimSpace(line)
		}
	}
	return ""
}

func countUserRows(lines []string) int {
	total := 0
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || !strings.Contains(trimmed, " | ") {
			continue
		}
		total++
	}
	return total
}

func (m Model) buildPalette() []paletteOption {
	return []paletteOption{
		{Title: "Dashboard", Description: "Operational health, tenant routing, security and resource summary.", Mode: paletteSwitch, Tab: 0},
		{Title: "Runtime", Description: "Quick switch to runtime mode control.", Mode: paletteSwitch, Tab: 1},
		{Title: "Databases", Description: "Quick switch to database operations.", Mode: paletteSwitch, Tab: 2},
		{Title: "Doctor", Description: "Quick switch to mode-specific diagnostics.", Mode: paletteSwitch, Tab: 3},
		{Title: "Logs", Description: "Quick switch to incidents and raw logs.", Mode: paletteSwitch, Tab: 4},
		{Title: "Config", Description: "Quick switch to setup, values and generate/validate.", Mode: paletteSwitch, Tab: 5},
		{
			Title:       "Start Stable Docker",
			Description: "Boot the stable docker runtime.",
			Mode:        paletteAction,
			Request: event.RequestMakeTargetMsg{
				Target:      "up",
				Description: "Start the stable Docker stack with the public-sector runtime.",
				RelevantKeys: []string{
					"DOMAIN", "PROD_DB_NAME", "OLLAMA_MODEL",
				},
			},
		},
		{
			Title:       "Start Stable Tunnel",
			Description: "Boot the public Cloudflare tunnel runtime.",
			Mode:        paletteAction,
			Request: event.RequestMakeTargetMsg{
				Target:      "up-tunnel",
				Description: "Start the public Cloudflare-published stack.",
				RelevantKeys: []string{
					"DOMAIN", "CLOUDFLARED_TOKEN",
				},
			},
		},
		{
			Title:       "Start Dev Host",
			Description: "Run native Odoo against local PostgreSQL after DB selection.",
			Mode:        paletteAction,
			Request: event.RequestMakeTargetMsg{
				Target:          "dev-safe",
				Description:     "Run native Odoo over local PostgreSQL after choosing a client database.",
				RelevantKeys:    []string{"DEV_HOST_HTTP_PORT", "PG_LOCAL_PORT"},
				SelectDatabase:  true,
				DatabaseBackend: "local",
			},
		},
		{
			Title:       "Start Dev Project",
			Description: "Run native Odoo against Docker PostgreSQL after DB selection.",
			Mode:        paletteAction,
			Request: event.RequestMakeTargetMsg{
				Target:          "dev",
				Description:     "Run native Odoo over Docker PostgreSQL after choosing a client database.",
				RelevantKeys:    []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"},
				SelectDatabase:  true,
				DatabaseBackend: "docker",
			},
		},
		{
			Title:       "Run Smoke",
			Description: "Execute smoke checks from the Makefile.",
			Mode:        paletteAction,
			Request: event.RequestMakeTargetMsg{
				Target:      "smoke",
				Description: "Run smoke checks.",
				RelevantKeys: []string{
					"DOMAIN", "LOCAL_HTTP_PORT",
				},
			},
		},
		{
			Title:       "Check Root Site",
			Description: "Validate kodoo.online locally and through the public edge.",
			Mode:        paletteAction,
			Request: event.RequestMakeTargetMsg{
				Target:      "root-smoke",
				Description: "Check the main kodoo.online website locally and publicly.",
				RelevantKeys: []string{
					"DOMAIN",
				},
			},
		},
		{
			Title:       "Run Troubleshoot",
			Description: "Execute the detailed diagnostics target.",
			Mode:        paletteAction,
			Request: event.RequestMakeTargetMsg{
				Target:      "troubleshoot",
				Description: "Run the detailed diagnostics target.",
				RelevantKeys: []string{
					"DOMAIN",
				},
			},
		},
	}
}

func (m Model) contextualStartStop() event.RequestMakeTargetMsg {
	switch m.snapshot.Runtime.Mode {
	case "Stable Docker", "Stable Tunnel":
		return event.RequestMakeTargetMsg{
			Target:            "down",
			Description:       "Stop the current Docker stack.",
			RelevantKeys:      []string{"DOMAIN"},
			RequireTypedCheck: true,
			ConfirmWord:       "sim",
		}
	case "Dev Host":
		return event.RequestMakeTargetMsg{
			Target:          "dev-safe",
			Description:     "Run native Odoo over local PostgreSQL after choosing a client database.",
			RelevantKeys:    []string{"DEV_HOST_HTTP_PORT", "PG_LOCAL_PORT"},
			SelectDatabase:  true,
			DatabaseBackend: "local",
		}
	case "Dev Project":
		return event.RequestMakeTargetMsg{
			Target:          "dev",
			Description:     "Run native Odoo over Docker PostgreSQL after choosing a client database.",
			RelevantKeys:    []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"},
			SelectDatabase:  true,
			DatabaseBackend: "docker",
		}
	default:
		return event.RequestMakeTargetMsg{
			Target:      "up",
			Description: "Start the stable Docker stack with the public-sector runtime.",
			RelevantKeys: []string{
				"DOMAIN", "PROD_DB_NAME", "OLLAMA_MODEL",
			},
		}
	}
}

func openEditor(path string) tea.Cmd {
	return func() tea.Msg {
		editor := strings.TrimSpace(os.Getenv("EDITOR"))
		if editor == "" {
			editor = "vi"
		}

		cmd := exec.Command(editor, path)
		cmd.Stdin = os.Stdin
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr

		if err := cmd.Run(); err != nil {
			return event.EditorDoneMsg{Path: path, Err: err}
		}
		return event.EditorDoneMsg{Path: path}
	}
}

func clearsActiveDB(target string) bool {
	switch target {
	case "down", "db-init", "doctor", "up", "up-tunnel":
		return true
	default:
		return false
	}
}

func tickCmd(interval time.Duration) tea.Cmd {
	return tea.Tick(interval, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
