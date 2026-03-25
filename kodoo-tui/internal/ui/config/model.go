package config

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/envconfig"
	"github.com/kodoo/kodoo-tui/internal/event"
	"github.com/kodoo/kodoo-tui/internal/state"
)

var (
	configPanelStyle = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	configTitleStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	mutedStyle       = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
	warnStyle        = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	okStyle          = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
)

type Model struct {
	cfg       *envconfig.Config
	snapshot  state.Snapshot
	width     int
	height    int
	table     table.Model
	search    textinput.Model
	searching bool
	input     textinput.Model
	editing   bool
	editKey   string
}

func New(cfg *envconfig.Config) Model {
	search := textinput.New()
	search.Placeholder = "search keys"
	search.Prompt = "/ "
	search.CharLimit = 120
	search.Blur()

	input := textinput.New()
	input.Prompt = "> "
	input.CharLimit = 4096
	input.Blur()

	tbl := table.New(
		table.WithColumns([]table.Column{
			{Title: "Key", Width: 28},
			{Title: "Value", Width: 30},
			{Title: "Origin", Width: 12},
			{Title: "Required", Width: 9},
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
	model.updateTableLayout()
	model.refreshRows()
	return model
}

func (m Model) Title() string {
	return "Config"
}

func (m Model) HelpLines() []string {
	if m.editing {
		lines := []string{
			"enter save value",
			"esc cancel edit",
		}
		if isLongSecretKey(m.editKey) {
			lines = append(lines, "paste the raw token/value; no quotes and no 'cole aqui'")
		}
		return lines
	}
	return []string{
		"/ search variables",
		"enter edit selected variable",
		"e open the active env file in $EDITOR",
		"p/h/j generate prod/dev-host/dev-project configs",
		"i create .env from the example file",
	}
}

func (m Model) SetConfig(cfg *envconfig.Config) Model {
	m.cfg = cfg
	m.refreshRows()
	return m
}

func (m Model) SetSnapshot(snapshot state.Snapshot) Model {
	m.snapshot = snapshot
	return m
}

func (m Model) Init() tea.Cmd {
	return nil
}

func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.updateTableLayout()
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
				m.input.CharLimit = charLimitForKey(m.editKey)
				m.input.SetValue(m.cfg.Value(m.editKey))
				m.input.Focus()
				return m, textinput.Blink
			}
		case "e":
			path := m.cfg.Path
			if path == "" {
				path = envconfig.PrimaryEnvFile
			}
			return m, requestCmd(event.RequestOpenEditorMsg{Path: path})
		case "p":
			return m, requestCmd(makeMsg("prod-config", "Generate deploy/odoo/kodoo.prod.local.conf.", []string{"PROD_DB_NAME", "PROD_DB_USER", "DOMAIN"}))
		case "h":
			return m, requestCmd(makeMsg("dev-host-config", "Generate deploy/odoo/kodoo.dev-host.local.conf.", []string{"DEV_HOST_HTTP_PORT", "PG_LOCAL_PORT"}))
		case "j":
			return m, requestCmd(makeMsg("dev-project-config", "Generate deploy/odoo/kodoo.dev-project.local.conf.", []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"}))
		case "i":
			return m, requestCmd(makeMsg("env-init", "Create .env from the example file.", []string{"DOMAIN", "EMAIL"}))
		}

		var cmd tea.Cmd
		m.table, cmd = m.table.Update(msg)
		return m, cmd
	}

	return m, nil
}

func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}

	panelWidth := max(24, width-2)
	topHeight, bottomHeight := m.panelHeights(height)
	middleHeight := max(8, height-topHeight-bottomHeight)

	top := configPanelStyle.Width(panelWidth).Height(topHeight).Render(m.summaryView(topHeight))
	middle := configPanelStyle.Width(panelWidth).Height(middleHeight).Render(m.tableView())
	bottom := configPanelStyle.Width(panelWidth).Height(bottomHeight).Render(m.shortcutsView(bottomHeight))
	return lipgloss.JoinVertical(lipgloss.Left, top, middle, bottom)
}

func (m Model) summaryView(height int) string {
	lines := []string{
		configTitleStyle.Render("Setup Wizard / Validation"),
		fmt.Sprintf("env file: %s", fallback(m.snapshot.Config.EnvPath, m.cfg.Path)),
		fmt.Sprintf("exists: %t", m.snapshot.Config.EnvExists),
		fmt.Sprintf("missing required keys: %d", len(m.snapshot.Config.MissingKeys)),
		fmt.Sprintf("db manager: %t", m.snapshot.Config.ProdListDB),
		fmt.Sprintf("dbfilter: %s", fallback(m.snapshot.Config.ProdDBFilter, m.cfg.Value("PROD_DBFILTER"))),
	}
	if m.snapshot.Config.UsesLegacyFile {
		lines = append(lines, warnStyle.Render("legacy fallback active: docker compose will expect .env"))
	}
	for path, ok := range m.snapshot.Config.GeneratedFiles {
		status := warnStyle.Render("missing")
		if ok {
			status = okStyle.Render("ok")
		}
		lines = append(lines, fmt.Sprintf("%s %s", status, path))
	}
	if len(m.snapshot.Config.MissingKeys) > 0 {
		lines = append(lines, warnStyle.Render("fill these first: "+strings.Join(m.snapshot.Config.MissingKeys, ", ")))
	}
	if tokenLooksTruncated(m.cfg.Value("CLOUDFLARED_TOKEN")) {
		lines = append(lines, warnStyle.Render("CLOUDFLARED_TOKEN looks truncated; re-paste the full raw token in Config"))
	}
	if !strings.Contains(fallback(m.snapshot.Config.ProdDBFilter, m.cfg.Value("PROD_DBFILTER")), "%d") {
		lines = append(lines, warnStyle.Render("recommended for tenant-per-subdomain mode: PROD_DBFILTER=^%d$"))
	}
	maxLines := max(3, height-2)
	if len(lines) > maxLines {
		lines = lines[:maxLines-1]
		lines = append(lines, mutedStyle.Render("..."))
	}
	return strings.Join(lines, "\n")
}

func (m Model) tableView() string {
	topLines := []string{configTitleStyle.Render("Config Values")}
	if m.editing {
		topLines = append(topLines, "Edit "+m.editKey+": "+m.input.View())
	} else if m.searching || m.search.Value() != "" {
		topLines = append(topLines, m.search.View())
	}
	if !m.cfg.Exists {
		topLines = append(topLines, warnStyle.Render(".env not found. Press i to create it."))
	}
	return strings.Join(topLines, "\n") + "\n\n" + m.table.View()
}

func (m Model) shortcutsView(height int) string {
	lines := []string{
		configTitleStyle.Render("Generate / Validate"),
		"p prod config  h dev-host  j dev-project  i init .env",
		"e edit env file  enter edit selected key  / search",
	}
	if height >= 6 {
		lines = append(lines, "Validation covers: .env, generated configs, required keys and DB reachability.")
	}
	maxLines := max(2, height-2)
	if len(lines) > maxLines {
		lines = lines[:maxLines]
	}
	return strings.Join(lines, "\n")
}

func (m *Model) updateTableLayout() {
	contentWidth := max(30, m.width-8)
	m.table.SetWidth(contentWidth)

	topHeight, bottomHeight := m.panelHeights(m.height)
	tableHeight := max(6, m.height-topHeight-bottomHeight-4)
	m.table.SetHeight(tableHeight)

	keyWidth, valueWidth, originWidth, requiredWidth := tableColumnWidths(contentWidth)
	m.table.SetColumns([]table.Column{
		{Title: "Key", Width: keyWidth},
		{Title: "Value", Width: valueWidth},
		{Title: "Origin", Width: originWidth},
		{Title: "Required", Width: requiredWidth},
	})
}

func (m Model) panelHeights(totalHeight int) (int, int) {
	switch {
	case totalHeight <= 20:
		return 5, 4
	case totalHeight <= 28:
		return 7, 5
	default:
		return 9, 7
	}
}

func tableColumnWidths(totalWidth int) (int, int, int, int) {
	requiredWidth := 8
	originWidth := 10

	switch {
	case totalWidth <= 54:
		requiredWidth = 6
		originWidth = 8
	case totalWidth <= 72:
		requiredWidth = 7
		originWidth = 9
	}

	remaining := totalWidth - originWidth - requiredWidth - 6
	if remaining < 20 {
		remaining = 20
	}

	keyWidth := max(12, remaining/3)
	valueWidth := max(12, remaining-keyWidth)
	return keyWidth, valueWidth, originWidth, requiredWidth
}

func (m *Model) refreshRows() {
	selectedKey := m.selectedKey()
	query := strings.ToLower(strings.TrimSpace(m.search.Value()))
	required := map[string]bool{
		"DOMAIN":                  true,
		"EMAIL":                   true,
		"PROD_DB_PASSWORD":        true,
		"PROD_ADMIN_PASSWORD":     true,
		"PG_LOCAL_PASSWORD":       true,
		"DEV_HOST_ADMIN_PASSWORD": true,
	}
	rows := make([]table.Row, 0, len(m.cfg.Values))
	for _, entry := range m.cfg.OrderedEntries() {
		if query != "" && !strings.Contains(strings.ToLower(entry.Key), query) && !strings.Contains(strings.ToLower(entry.Value), query) {
			continue
		}
		requiredFlag := ""
		if required[entry.Key] {
			requiredFlag = "yes"
		}
		rows = append(rows, table.Row{entry.Key, m.cfg.MaskedValue(entry.Key), entry.Source, requiredFlag})
	}
	m.table.SetRows(rows)
	m.restoreSelection(selectedKey, len(rows))
}

func (m Model) selectedKey() string {
	row := m.table.SelectedRow()
	if len(row) == 0 {
		return ""
	}
	return row[0]
}

func (m *Model) restoreSelection(key string, size int) {
	if size == 0 {
		m.table.SetCursor(0)
		return
	}
	if key != "" {
		for idx, row := range m.table.Rows() {
			if len(row) > 0 && row[0] == key {
				m.table.SetCursor(idx)
				return
			}
		}
	}
	cursor := m.table.Cursor()
	if cursor >= size {
		m.table.SetCursor(size - 1)
	}
}

func makeMsg(target, description string, relevant []string) tea.Msg {
	return event.RequestMakeTargetMsg{
		Target:       target,
		Description:  description,
		RelevantKeys: relevant,
	}
}

func charLimitForKey(key string) int {
	if isLongSecretKey(key) {
		return 4096
	}
	return 512
}

func isLongSecretKey(key string) bool {
	upper := strings.ToUpper(strings.TrimSpace(key))
	return strings.Contains(upper, "TOKEN") || strings.Contains(upper, "PASSWORD")
}

func tokenLooksTruncated(value string) bool {
	value = strings.TrimSpace(value)
	return len(value) == 200
}

func requestCmd(msg tea.Msg) tea.Cmd {
	return func() tea.Msg { return msg }
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
