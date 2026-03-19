package dashboard

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/progress"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/docker"
	"github.com/kodoo/kodoo-tui/internal/envconfig"
	"github.com/kodoo/kodoo-tui/internal/event"
)

var (
	serviceTitleStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	okStyle           = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
	warnStyle         = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	errStyle          = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	mutedStyle        = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
	boxStyle          = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
)

type tickMsg time.Time

type refreshMsg struct {
	containers []docker.Container
	stats      []docker.Stat
	logs       []string
	mode       string
	err        error
}

// Model renders the main dashboard tab.
type Model struct {
	cfg         *envconfig.Config
	width       int
	height      int
	containers  []docker.Container
	stats       []docker.Stat
	logs        []string
	events      viewport.Model
	lastUpdated time.Time
	mode        string
	err         string
}

// New builds the dashboard tab model.
func New(cfg *envconfig.Config) Model {
	vp := viewport.New(20, 10)
	return Model{
		cfg:    cfg,
		events: vp,
		mode:   detectMode(nil),
	}
}

// Title returns the visible tab name.
func (m Model) Title() string {
	return "Dashboard"
}

// HelpLines returns the dashboard help text.
func (m Model) HelpLines() []string {
	return []string{
		"u  start the stable public-sector Docker stack",
		"b  start the stable plain Odoo Docker stack",
		"d  stop the active Docker stack",
		"r  run make refresh-safe",
		"s  run make smoke",
		"l  open the launchpad",
	}
}

// SetConfig updates the live config pointer after reloads.
func (m Model) SetConfig(cfg *envconfig.Config) Model {
	m.cfg = cfg
	return m
}

// Mode returns the currently inferred runtime mode.
func (m Model) Mode() string {
	if m.mode == "" {
		return detectMode(m.containers)
	}
	return m.mode
}

// Init starts the periodic refresh loop.
func (m Model) Init() tea.Cmd {
	return tea.Batch(refreshCmd(m.cfg), tickCmd(m.cfg.RefreshInterval()))
}

// Update handles Bubble Tea messages for the dashboard.
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.syncViewport()
	case tickMsg:
		return m, tea.Batch(refreshCmd(m.cfg), tickCmd(m.cfg.RefreshInterval()))
	case refreshMsg:
		if msg.err != nil {
			m.err = msg.err.Error()
		} else {
			m.err = ""
		}
		m.containers = msg.containers
		m.stats = msg.stats
		m.logs = msg.logs
		m.mode = msg.mode
		m.lastUpdated = time.Now()
		m.syncViewport()
	case tea.KeyMsg:
		switch msg.String() {
		case "u":
			return m, requestCmd(event.RequestMakeTargetMsg{
				Target:      "up",
				Description: "Start the stable Docker stack with the public-sector runtime.",
				RelevantKeys: []string{
					"DOMAIN", "LOCAL_HTTP_PORT", "OLLAMA_MODEL",
				},
			})
		case "b":
			return m, requestCmd(event.RequestMakeTargetMsg{
				Target:      "up-base",
				Description: "Start the stable Docker stack with the plain Odoo runtime.",
				RelevantKeys: []string{
					"DOMAIN", "LOCAL_HTTP_PORT", "OLLAMA_MODEL",
				},
			})
		case "d":
			return m, requestCmd(event.RequestMakeTargetMsg{
				Target:            "down",
				Description:       "Stop the current Docker stack.",
				RequireTypedCheck: true,
				ConfirmWord:       "sim",
				RelevantKeys:      []string{"DOMAIN"},
			})
		case "r":
			return m, requestCmd(event.RequestMakeTargetMsg{
				Target:      "refresh-safe",
				Description: "Regenerate configs and restart only the stable Odoo service.",
				RelevantKeys: []string{
					"DOMAIN", "PROD_DB_NAME", "PROD_DB_USER",
				},
			})
		case "s":
			return m, requestCmd(event.RequestMakeTargetMsg{
				Target:      "smoke",
				Description: "Run the smoke checks defined by the Makefile.",
				RelevantKeys: []string{
					"DOMAIN", "LOCAL_HTTP_PORT", "SMOKE_PUBLIC",
				},
			})
		}
	}

	return m, nil
}

// View renders the dashboard tab.
func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}

	colWidth := max(24, (width-4)/3)
	left := boxStyle.Width(colWidth).Height(max(8, height-4)).Render(m.servicesView())
	middle := boxStyle.Width(colWidth).Height(max(8, height-4)).Render(m.resourcesView(colWidth - 4))
	right := boxStyle.Width(width - (colWidth * 2) - 8).Height(max(8, height-4)).Render(m.eventsView())

	return lipgloss.JoinHorizontal(lipgloss.Top, left, middle, right)
}

func (m Model) servicesView() string {
	lines := []string{serviceTitleStyle.Render("Services")}
	if !m.cfg.Exists {
		lines = append(lines, warnStyle.Render(".env.make missing. Run make env-init"))
	}
	if m.err != "" {
		lines = append(lines, errStyle.Render(m.err))
	}
	if len(m.containers) == 0 {
		lines = append(lines, mutedStyle.Render("No containers detected in Docker."))
		return strings.Join(lines, "\n")
	}

	sort.Slice(m.containers, func(i, j int) bool {
		return m.containers[i].Name < m.containers[j].Name
	})

	for _, container := range m.containers {
		color := lipgloss.Color("42")
		status := strings.ToLower(container.Status)
		switch {
		case strings.Contains(status, "restarting"):
			color = lipgloss.Color("214")
		case strings.Contains(status, "exited") || strings.Contains(status, "dead"):
			color = lipgloss.Color("196")
		}
		dot := lipgloss.NewStyle().Foreground(color).Render("●")
		lines = append(lines, fmt.Sprintf("%s %s", dot, container.Name))
		lines = append(lines, mutedStyle.Render("  "+container.Status))
		lines = append(lines, mutedStyle.Render("  image: "+container.Image))
		if strings.TrimSpace(container.Ports) != "" {
			lines = append(lines, mutedStyle.Render("  ports: "+container.Ports))
		}
	}
	return strings.Join(lines, "\n")
}

func (m Model) resourcesView(contentWidth int) string {
	lines := []string{
		serviceTitleStyle.Render("Resources"),
		fmt.Sprintf("Mode: %s", okStyle.Render(m.Mode())),
		fmt.Sprintf("Runtime: %s", runtimeProfile(m.containers)),
		fmt.Sprintf("Ports: %s", mutedStyle.Render(m.portSummary())),
		"",
	}
	if len(m.stats) == 0 {
		lines = append(lines, mutedStyle.Render("No docker stats available."))
		return strings.Join(lines, "\n")
	}

	for _, stat := range m.stats {
		barWidth := max(10, contentWidth-18)
		bar := progress.New(progress.WithWidth(barWidth))
		cpuView := bar.ViewAs(clamp(stat.CPUPercent / 100))
		memView := bar.ViewAs(clamp(stat.MemPercent / 100))
		lines = append(lines, fmt.Sprintf("%s", lipgloss.NewStyle().Bold(true).Render(stat.Name)))
		lines = append(lines, fmt.Sprintf("CPU %5.1f%% %s", stat.CPUPercent, cpuView))
		lines = append(lines, fmt.Sprintf("MEM %5.1f%% %s", stat.MemPercent, memView))
		if stat.MemUsage != "" {
			lines = append(lines, mutedStyle.Render("  "+stat.MemUsage))
		}
		lines = append(lines, "")
	}

	if !m.lastUpdated.IsZero() {
		lines = append(lines, mutedStyle.Render("Updated "+m.lastUpdated.Format("15:04:05")))
	}
	return strings.Join(lines, "\n")
}

func (m Model) eventsView() string {
	header := serviceTitleStyle.Render("Recent Events")
	if len(m.logs) == 0 {
		return header + "\n" + mutedStyle.Render("No compose logs available.")
	}
	return header + "\n" + m.events.View()
}

func (m *Model) syncViewport() {
	width := max(16, m.rightColumnWidth()-4)
	height := max(6, m.height-9)
	m.events.Width = width
	m.events.Height = height

	lines := make([]string, 0, len(m.logs))
	for _, line := range m.logs {
		lines = append(lines, colorizeLogLine(line))
	}
	m.events.SetContent(strings.Join(lines, "\n"))
	m.events.GotoBottom()
}

func (m Model) rightColumnWidth() int {
	if m.width <= 0 {
		return 24
	}
	colWidth := max(24, (m.width-4)/3)
	return m.width - (colWidth * 2) - 8
}

func (m Model) portSummary() string {
	parts := make([]string, 0, len(m.containers))
	for _, container := range m.containers {
		if strings.TrimSpace(container.Ports) == "" {
			continue
		}
		parts = append(parts, fmt.Sprintf("%s: %s", container.Name, container.Ports))
	}
	if len(parts) == 0 {
		return "no published ports"
	}
	return strings.Join(parts, " | ")
}

func refreshCmd(cfg *envconfig.Config) tea.Cmd {
	return func() tea.Msg {
		containers, err := docker.ListContainers()
		if err != nil {
			return refreshMsg{err: err}
		}
		stats, _ := docker.Stats()
		logs, _ := docker.TailLogs(cfg.TUILogLines, "todos")
		return refreshMsg{
			containers: containers,
			stats:      stats,
			logs:       logs,
			mode:       detectMode(containers),
		}
	}
}

func tickCmd(interval time.Duration) tea.Cmd {
	return tea.Tick(interval, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func detectMode(containers []docker.Container) string {
	if pidRunning(filepath.Join("logs", "odoo-dev-project.pid")) {
		return "client dev · docker db"
	}
	if pidRunning(filepath.Join("logs", "odoo-dev-host.pid")) {
		return "client dev · local db"
	}

	runtime := runtimeProfile(containers)
	if runtime != "unknown runtime" {
		if containerRunning(containers, "kodoo-cloudflared") {
			return "stable tunnel · " + runtime
		}
		if containerRunning(containers, "kodoo-odoo") {
			return "stable docker · " + runtime
		}
		if containerExists(containers, "kodoo-odoo") {
			return "stable docker stopped · " + runtime
		}
	}
	return "idle"
}

func runtimeProfile(containers []docker.Container) string {
	for _, container := range containers {
		if container.Name != "kodoo-odoo" {
			continue
		}
		switch {
		case strings.Contains(container.Image, "19.0-public-sector"), strings.Contains(container.Image, "19.0-agi-gov"), strings.Contains(container.Image, "19.0-gov"):
			return "public-sector runtime"
		case strings.Contains(container.Image, "19.0"):
			return "plain runtime"
		default:
			return container.Image
		}
	}
	return "unknown runtime"
}

func containerRunning(containers []docker.Container, name string) bool {
	for _, container := range containers {
		if container.Name != name {
			continue
		}
		status := strings.ToLower(container.Status)
		return strings.HasPrefix(status, "up") || strings.Contains(status, "running")
	}
	return false
}

func containerExists(containers []docker.Container, name string) bool {
	for _, container := range containers {
		if container.Name == name {
			return true
		}
	}
	return false
}

func pidRunning(path string) bool {
	data, err := os.ReadFile(path)
	if err != nil {
		return false
	}
	pid := strings.TrimSpace(string(data))
	if pid == "" {
		return false
	}
	_, err = os.Stat(filepath.Clean("/proc/" + pid))
	return err == nil
}

func colorizeLogLine(line string) string {
	service := ""
	rest := line
	if parts := strings.SplitN(line, "|", 2); len(parts) == 2 {
		service = strings.TrimSpace(parts[0])
		rest = strings.TrimSpace(parts[1])
	}

	if service != "" {
		palette := map[string]lipgloss.Style{
			"odoo":        lipgloss.NewStyle().Foreground(lipgloss.Color("33")),
			"nginx":       lipgloss.NewStyle().Foreground(lipgloss.Color("42")),
			"db":          lipgloss.NewStyle().Foreground(lipgloss.Color("214")),
			"cloudflared": lipgloss.NewStyle().Foreground(lipgloss.Color("99")),
			"ollama":      lipgloss.NewStyle().Foreground(lipgloss.Color("205")),
		}
		style := palette[service]
		if style.String() == "" {
			style = mutedStyle
		}
		return style.Render(service) + " | " + rest
	}
	return rest
}

func requestCmd(msg tea.Msg) tea.Cmd {
	return func() tea.Msg { return msg }
}

func clamp(value float64) float64 {
	if value < 0 {
		return 0
	}
	if value > 1 {
		return 1
	}
	return value
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
