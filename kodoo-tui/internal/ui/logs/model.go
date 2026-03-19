package logs

import (
	"context"
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/docker"
	"github.com/kodoo/kodoo-tui/internal/envconfig"
)

var (
	logBoxStyle      = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	selectedLogStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	errorLineStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	warnLineStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	matchStyle       = lipgloss.NewStyle().Bold(true).Underline(true)
)

type servicesLoadedMsg struct {
	services []string
	err      error
}

type streamLineMsg struct {
	line string
	done bool
}

// Model renders the logs tab.
type Model struct {
	cfg       *envconfig.Config
	width     int
	height    int
	services  []string
	selected  int
	lines     []string
	viewport  viewport.Model
	filter    textinput.Model
	searching bool
	follow    bool
	cancel    context.CancelFunc
	stream    <-chan string
	err       string
}

// New builds the logs tab model.
func New(cfg *envconfig.Config) Model {
	filter := textinput.New()
	filter.Placeholder = "filter logs"
	filter.Prompt = "/ "
	filter.CharLimit = 120
	filter.Blur()
	return Model{
		cfg:      cfg,
		services: []string{"todos"},
		viewport: viewport.New(40, 10),
		filter:   filter,
		follow:   true,
	}
}

// Title returns the visible tab label.
func (m Model) Title() string {
	return "Logs"
}

// HelpLines returns the logs help text.
func (m Model) HelpLines() []string {
	return []string{
		"↑/↓  choose service",
		"/    search in visible logs",
		"f    toggle follow mode",
		"c    clear the current log buffer",
	}
}

// SetConfig updates the config pointer.
func (m Model) SetConfig(cfg *envconfig.Config) Model {
	m.cfg = cfg
	return m
}

// Init loads services and starts the first log stream.
func (m Model) Init() tea.Cmd {
	return loadServicesCmd()
}

// Update handles log messages and user input.
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.syncViewport()
	case servicesLoadedMsg:
		if msg.err != nil {
			m.err = msg.err.Error()
			return m, nil
		}
		m.services = msg.services
		return m, m.restartStream()
	case streamLineMsg:
		if msg.done {
			return m, nil
		}
		m.lines = append(m.lines, msg.line)
		if len(m.lines) > 2000 {
			m.lines = m.lines[len(m.lines)-2000:]
		}
		m.syncViewport()
		if m.stream != nil {
			return m, waitStreamCmd(m.stream)
		}
	case tea.KeyMsg:
		if m.searching {
			switch msg.String() {
			case "esc":
				m.searching = false
				m.filter.Blur()
				m.syncViewport()
				return m, nil
			}
			var cmd tea.Cmd
			m.filter, cmd = m.filter.Update(msg)
			m.syncViewport()
			return m, cmd
		}

		switch msg.String() {
		case "up":
			m.moveSelection(-1)
			return m, m.restartStream()
		case "down":
			m.moveSelection(1)
			return m, m.restartStream()
		case "/":
			m.searching = true
			m.filter.Focus()
			return m, textinput.Blink
		case "f":
			m.follow = !m.follow
			m.syncViewport()
		case "c":
			m.lines = nil
			m.syncViewport()
		}
	}

	return m, nil
}

// View renders the logs tab.
func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}

	sidebarWidth := min(24, max(18, width/5))
	sidebar := logBoxStyle.Width(sidebarWidth).Height(max(8, height-4)).Render(m.servicesView())
	main := logBoxStyle.Width(width - sidebarWidth - 4).Height(max(8, height-4)).Render(m.logView())
	return lipgloss.JoinHorizontal(lipgloss.Top, sidebar, main)
}

func (m Model) servicesView() string {
	lines := []string{selectedLogStyle.Render("Services")}
	for idx, service := range m.services {
		style := lipgloss.NewStyle()
		prefix := "  "
		if idx == m.selected {
			style = selectedLogStyle
			prefix = "> "
		}
		lines = append(lines, style.Render(prefix+service))
	}
	if m.err != "" {
		lines = append(lines, "", errorLineStyle.Render(m.err))
	}
	return strings.Join(lines, "\n")
}

func (m Model) logView() string {
	meta := []string{
		selectedLogStyle.Render("Compose Logs"),
		fmt.Sprintf("service: %s", m.currentService()),
		fmt.Sprintf("follow: %t", m.follow),
	}
	if m.searching || m.filter.Value() != "" {
		meta = append(meta, m.filter.View())
	}
	return strings.Join(meta, "\n") + "\n\n" + m.viewport.View()
}

func (m *Model) moveSelection(delta int) {
	if len(m.services) == 0 {
		return
	}
	m.selected += delta
	if m.selected < 0 {
		m.selected = 0
	}
	if m.selected >= len(m.services) {
		m.selected = len(m.services) - 1
	}
}

func (m *Model) syncViewport() {
	m.viewport.Width = max(20, m.width-min(24, max(18, m.width/5))-10)
	m.viewport.Height = max(6, m.height-10)
	rendered := make([]string, 0, len(m.lines))
	for _, line := range m.filteredLines() {
		rendered = append(rendered, highlightLogLine(line, m.filter.Value()))
	}
	m.viewport.SetContent(strings.Join(rendered, "\n"))
	if m.follow {
		m.viewport.GotoBottom()
	}
}

func (m Model) filteredLines() []string {
	query := strings.TrimSpace(strings.ToLower(m.filter.Value()))
	if query == "" {
		return append([]string(nil), m.lines...)
	}

	filtered := make([]string, 0, len(m.lines))
	for _, line := range m.lines {
		if strings.Contains(strings.ToLower(line), query) {
			filtered = append(filtered, line)
		}
	}
	return filtered
}

func (m *Model) restartStream() tea.Cmd {
	if m.cancel != nil {
		m.cancel()
	}

	ctx, cancel := context.WithCancel(context.Background())
	ch := make(chan string, 32)
	m.cancel = cancel
	m.stream = ch
	m.lines = nil
	m.syncViewport()

	return tea.Batch(
		func() tea.Msg {
			go docker.StreamLogs(ctx, m.currentService(), m.cfg.TUILogLines, ch)
			return nil
		},
		waitStreamCmd(ch),
	)
}

func (m Model) currentService() string {
	if len(m.services) == 0 {
		return "todos"
	}
	if m.selected < 0 || m.selected >= len(m.services) {
		return m.services[0]
	}
	return m.services[m.selected]
}

func loadServicesCmd() tea.Cmd {
	return func() tea.Msg {
		services, err := docker.Services()
		return servicesLoadedMsg{services: services, err: err}
	}
}

func waitStreamCmd(ch <-chan string) tea.Cmd {
	return func() tea.Msg {
		line, ok := <-ch
		if !ok {
			return streamLineMsg{done: true}
		}
		return streamLineMsg{line: line}
	}
}

func highlightLogLine(line, query string) string {
	styled := line
	upper := strings.ToUpper(line)
	switch {
	case strings.Contains(upper, "ERROR"), strings.Contains(upper, "CRITICAL"):
		styled = errorLineStyle.Render(line)
	case strings.Contains(upper, "WARNING"):
		styled = warnLineStyle.Render(line)
	}

	query = strings.TrimSpace(query)
	if query == "" {
		return styled
	}

	lower := strings.ToLower(line)
	matchAt := strings.Index(lower, strings.ToLower(query))
	if matchAt < 0 {
		return styled
	}

	before := line[:matchAt]
	match := line[matchAt : matchAt+len(query)]
	after := line[matchAt+len(query):]
	return before + matchStyle.Render(match) + after
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
