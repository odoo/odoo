package config

import (
	"strings"

	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/envconfig"
	"github.com/kodoo/kodoo-tui/internal/event"
)

var (
	configPanelStyle = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	configTitleStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
)

// Model renders the config tab.
type Model struct {
	cfg       *envconfig.Config
	width     int
	height    int
	table     table.Model
	search    textinput.Model
	searching bool
	input     textinput.Model
	editing   bool
	editKey   string
}

// New builds the config tab model.
func New(cfg *envconfig.Config) Model {
	search := textinput.New()
	search.Placeholder = "search keys"
	search.Prompt = "/ "
	search.CharLimit = 120
	search.Blur()

	input := textinput.New()
	input.Prompt = "> "
	input.CharLimit = 200
	input.Blur()

	tbl := table.New(
		table.WithColumns([]table.Column{
			{Title: "Key", Width: 28},
			{Title: "Value", Width: 40},
			{Title: "Origin", Width: 12},
		}),
		table.WithFocused(true),
		table.WithHeight(12),
	)

	model := Model{
		cfg:    cfg,
		table:  tbl,
		search: search,
		input:  input,
	}
	model.refreshRows()
	return model
}

// Title returns the visible tab label.
func (m Model) Title() string {
	return "Config"
}

// HelpLines returns the config help text.
func (m Model) HelpLines() []string {
	if m.editing {
		return []string{
			"enter  save value",
			"esc    cancel edit",
		}
	}
	return []string{
		"/      search variables",
		"enter  edit selected variable",
		"e      open .env.make in $EDITOR",
		"p/h/j/i generate prod/dev-host/dev-project configs or env-init",
	}
}

// SetConfig updates the config pointer and table rows.
func (m Model) SetConfig(cfg *envconfig.Config) Model {
	m.cfg = cfg
	m.refreshRows()
	return m
}

// Init does not need background work.
func (m Model) Init() tea.Cmd {
	return nil
}

// Update handles config tab input.
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.table.SetWidth(max(30, m.width-8))
		m.table.SetHeight(max(8, m.height-12))
	case tea.KeyMsg:
		if m.editing {
			switch msg.String() {
			case "esc":
				m.editing = false
				m.input.Blur()
				return m, nil
			case "enter":
				key := m.editKey
				value := m.input.Value()
				m.editing = false
				m.input.Blur()
				return m, func() tea.Msg {
					return event.RequestUpdateConfigMsg{Key: key, Value: value}
				}
			}
			var cmd tea.Cmd
			m.input, cmd = m.input.Update(msg)
			return m, cmd
		}

		if m.searching {
			switch msg.String() {
			case "esc":
				m.searching = false
				m.search.Blur()
				m.refreshRows()
				return m, nil
			case "enter":
				m.searching = false
				m.search.Blur()
				return m, nil
			}
			var cmd tea.Cmd
			m.search, cmd = m.search.Update(msg)
			m.refreshRows()
			return m, cmd
		}

		switch msg.String() {
		case "/":
			m.searching = true
			m.search.Focus()
			return m, textinput.Blink
		case "enter":
			row := m.table.SelectedRow()
			if len(row) > 0 {
				m.editing = true
				m.editKey = row[0]
				m.input.SetValue(m.cfg.Value(m.editKey))
				m.input.Focus()
				return m, textinput.Blink
			}
		case "e":
			return m, requestCmd(event.RequestOpenEditorMsg{Path: ".env.make"})
		case "p":
			return m, requestCmd(makeMsg("prod-config", "Generate deploy/odoo/kodoo.prod.local.conf.", []string{"PROD_DB_NAME", "PROD_DB_USER", "DOMAIN"}))
		case "h":
			return m, requestCmd(makeMsg("dev-host-config", "Generate deploy/odoo/kodoo.dev-host.local.conf.", []string{"DEV_HOST_HTTP_PORT", "PG_LOCAL_PORT"}))
		case "j":
			return m, requestCmd(makeMsg("dev-project-config", "Generate deploy/odoo/kodoo.dev-project.local.conf.", []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"}))
		case "i":
			return m, requestCmd(makeMsg("env-init", "Create .env.make from the example file.", []string{"DOMAIN", "EMAIL"}))
		}

		var cmd tea.Cmd
		m.table, cmd = m.table.Update(msg)
		return m, cmd
	}

	return m, nil
}

// View renders the config tab.
func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}

	topLines := []string{
		configTitleStyle.Render("Active Variables"),
	}
	if m.editing {
		topLines = append(topLines, "Edit "+m.editKey+": "+m.input.View())
	} else if m.searching || m.search.Value() != "" {
		topLines = append(topLines, m.search.View())
	}
	if !m.cfg.Exists {
		topLines = append(topLines, lipgloss.NewStyle().Foreground(lipgloss.Color("214")).Render(".env.make not found. Press i to create it."))
	}

	top := configPanelStyle.Width(width - 2).Height(max(10, height-12)).Render(strings.Join(topLines, "\n") + "\n\n" + m.table.View())
	bottom := configPanelStyle.Width(width - 2).Height(7).Render(strings.Join([]string{
		configTitleStyle.Render("Config Actions"),
		"p  make prod-config",
		"h  make dev-host-config",
		"j  make dev-project-config",
		"i  make env-init",
		"e  open .env.make",
		"enter  edit selected",
	}, "\n"))
	return lipgloss.JoinVertical(lipgloss.Left, top, bottom)
}

func (m *Model) refreshRows() {
	query := strings.ToLower(strings.TrimSpace(m.search.Value()))
	rows := make([]table.Row, 0, len(m.cfg.Values))
	for _, entry := range m.cfg.OrderedEntries() {
		if query != "" && !strings.Contains(strings.ToLower(entry.Key), query) && !strings.Contains(strings.ToLower(entry.Value), query) {
			continue
		}
		rows = append(rows, table.Row{entry.Key, m.cfg.MaskedValue(entry.Key), entry.Source})
	}
	m.table.SetRows(rows)
}

func makeMsg(target, description string, relevant []string) tea.Msg {
	return event.RequestMakeTargetMsg{
		Target:       target,
		Description:  description,
		RelevantKeys: relevant,
	}
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
