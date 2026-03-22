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
	"github.com/kodoo/kodoo-tui/internal/state"
)

type servicesLoadedMsg struct {
	services []string
	err      error
}

type streamLineMsg struct {
	line string
	done bool
}

type viewMode int

const (
	incidentsView viewMode = iota
	rawLogsView
)

type Model struct {
	snapshot  state.Snapshot
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
	view      viewMode
}

var (
	logBoxStyle      = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	selectedLogStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	errorLineStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	warnLineStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	mutedStyle       = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
	matchStyle       = lipgloss.NewStyle().Bold(true).Underline(true)
	okStyle          = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
)

func New() Model {
	filter := textinput.New()
	filter.Placeholder = "filter logs"
	filter.Prompt = "/ "
	filter.CharLimit = 120
	filter.Blur()
	return Model{
		services: []string{"todos"},
		viewport: viewport.New(40, 10),
		filter:   filter,
		follow:   true,
		view:     incidentsView,
	}
}

func (m Model) Title() string {
	return "Logs"
}

func (m Model) HelpLines() []string {
	if m.view == incidentsView {
		return []string{
			"left/right switch between incidents and raw logs",
			"enter on incidents is not required; logs are diagnostic first here",
		}
	}
	return []string{
		"left/right switch between incidents and raw logs",
		"↑/↓ choose service",
		"/ search in visible logs",
		"f toggle follow mode",
		"c clear the current log buffer",
	}
}

func (m Model) Init() tea.Cmd {
	return loadServicesCmd()
}

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
		case "left", "h":
			m.view = incidentsView
		case "right", "raw", "i":
			m.view = rawLogsView
		}

		if m.view == incidentsView {
			return m, nil
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

func (m Model) SetSnapshot(snapshot state.Snapshot) Model {
	m.snapshot = snapshot
	return m
}

func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}
	if m.view == incidentsView {
		return logBoxStyle.Width(width - 2).Height(max(8, height-4)).Render(m.incidentsPane())
	}

	sidebarWidth := min(24, max(18, width/5))
	sidebar := logBoxStyle.Width(sidebarWidth).Height(max(8, height-4)).Render(m.servicesView())
	main := logBoxStyle.Width(width - sidebarWidth - 4).Height(max(8, height-4)).Render(m.logView())
	return lipgloss.JoinHorizontal(lipgloss.Top, sidebar, main)
}

func (m Model) incidentsPane() string {
	lines := []string{
		selectedLogStyle.Render("Incidents"),
		mutedStyle.Render("left/right to switch to Raw Logs"),
	}
	if len(m.snapshot.Incidents) == 0 {
		lines = append(lines, "", okStyle.Render("No incidents detected in the latest snapshot."))
		return strings.Join(lines, "\n")
	}
	for _, incident := range m.snapshot.Incidents {
		lines = append(lines, "", fmt.Sprintf("%s %s", severityDot(incident.Severity), incident.Summary))
		lines = append(lines, mutedStyle.Render(incident.Cause))
		lines = append(lines, warnLineStyle.Render("next: "+incident.Suggestion))
	}
	return strings.Join(lines, "\n")
}

func (m Model) servicesView() string {
	lines := []string{
		selectedLogStyle.Render("Raw Logs"),
		mutedStyle.Render("left/right to switch to Incidents"),
	}
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
			go docker.StreamLogs(ctx, m.currentService(), 20, ch)
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

func severityDot(level state.Severity) string {
	switch level {
	case state.SeverityCritical:
		return errorLineStyle.Render("●")
	case state.SeverityWarning:
		return warnLineStyle.Render("●")
	default:
		return okStyle.Render("●")
	}
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
