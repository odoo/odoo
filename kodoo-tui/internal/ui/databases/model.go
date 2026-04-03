package databases

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/envconfig"
	"github.com/kodoo/kodoo-tui/internal/event"
	"github.com/kodoo/kodoo-tui/internal/state"
)

type Model struct {
	cfg      *envconfig.Config
	snapshot state.Snapshot
	selected int
}

var (
	titleStyle       = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	panelStyle       = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	selectedStyle    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	mutedStyle       = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
	okStyle          = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
	warnStyle        = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	errStyle         = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	actionChipStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("16")).Background(lipgloss.Color("86")).Padding(0, 1)
	neutralChipStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("252")).Background(lipgloss.Color("240")).Padding(0, 1)
	dangerChipStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("255")).Background(lipgloss.Color("160")).Padding(0, 1)
	blockedChipStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("252")).Background(lipgloss.Color("238")).Padding(0, 1)
)

func New(cfg *envconfig.Config) Model {
	return Model{cfg: cfg}
}

func (m Model) Title() string {
	return "Databases"
}

func (m Model) HelpLines() []string {
	return []string{
		"↑/↓ move between databases",
		"mouse click selects a database, wheel scrolls the list, tab click switches screens",
		"enter use selected database in the best matching mode",
		"m manager, o bootstrap defaults, a adjust, D delete db, x reset, u users, p reset password, y operator, g portal, i internal, c create client, v validate via db-list",
	}
}

func (m Model) Init() tea.Cmd {
	return nil
}

func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "up":
			if m.selected > 0 {
				m.selected--
			}
		case "down":
			if m.selected < len(m.snapshot.Databases)-1 {
				m.selected++
			}
		case "enter":
			if req, ok := m.useRequest(); ok {
				return m, requestCmd(req)
			}
		case "m":
			return m, requestCmd(event.RequestMakeTargetMsg{
				Target:      "db-init",
				Description: "Open the Odoo database manager against Docker PostgreSQL.",
				RelevantKeys: []string{
					"DEV_PROJECT_DB",
				},
			})
		case "b":
			if current, ok := m.current(); ok && current.Backend == "local" {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:      "dev-host-backup",
					Description: "Create a local PostgreSQL backup.",
					RelevantKeys: []string{
						"DEV_HOST_DB", "BACKUP_DIR",
					},
					Vars: map[string]string{"DB": current.Name},
				})
			}
		case "r":
			if current, ok := m.current(); ok && current.Backend == "local" {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:            "dev-host-restore-ktest",
					Description:       "Restore the latest backup into the local ktest database.",
					RelevantKeys:      []string{"DEV_HOST_TEST_DB", "BACKUP_DIR"},
					RequireTypedCheck: true,
					ConfirmWord:       "sim",
				})
			}
		case "v":
			return m, requestCmd(event.RequestMakeTargetMsg{
				Target:      "db-list",
				Description: "List the available databases to validate connectivity.",
				RelevantKeys: []string{
					"DEV_PROJECT_DB", "DEV_HOST_TEST_DB",
				},
			})
		case "a":
			if current, ok := m.current(); ok {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:      "tenant-adjust",
					Description: "Reapply tenant URL/freeze and rerun isolation checks.",
					RelevantKeys: []string{
						"DOMAIN", "PROD_DB_NAME",
					},
					Vars: map[string]string{"DB": current.Name},
				})
			}
		case "o":
			if current, ok := m.current(); ok {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:      "tenant-bootstrap-defaults",
					Description: "Apply company/admin/lang/currency defaults to the selected tenant database.",
					RelevantKeys: []string{
						"DOMAIN", "TENANT_DEFAULT_LANG", "TENANT_DEFAULT_CURRENCY", "TENANT_ADMIN_LOGIN",
					},
					Vars: map[string]string{"DB": current.Name},
				})
			}
		case "x":
			if current, ok := m.current(); ok {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:            "tenant-reset",
					Description:       "Drop and recreate the selected tenant database using the configured tenant profile.",
					RelevantKeys:      []string{"DOMAIN", "PROD_DB_NAME", "TENANT_PROFILE"},
					RequireTypedCheck: true,
					ConfirmWord:       "sim",
					Vars:              map[string]string{"DB": current.Name},
				})
			}
		case "D", "delete":
			if req, ok := m.dropRequest(); ok {
				return m, requestCmd(req)
			}
		case "u":
			if current, ok := m.current(); ok {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:      "tenant-user-list",
					Description: "List interactive users in the selected database.",
					RelevantKeys: []string{
						"PROD_DB_NAME",
					},
					Vars: map[string]string{"DB": current.Name},
				})
			}
		case "p":
			if current, ok := m.current(); ok {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:      "tenant-user-password",
					Description: "Reset one user password inside the selected database.",
					RelevantKeys: []string{
						"PROD_DB_NAME",
					},
					PromptFields: []event.PromptField{
						{Key: "LOGIN", Label: "User login", Placeholder: "admin or email"},
						{Key: "PASSWORD", Label: "New password", Placeholder: "new password", Secret: true},
					},
					Vars: map[string]string{"DB": current.Name},
				})
			}
		case "g":
			if current, ok := m.current(); ok {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:      "tenant-user-role",
					Description: "Grant portal access to one user inside the selected database.",
					RelevantKeys: []string{
						"PROD_DB_NAME",
					},
					PromptFields: []event.PromptField{
						{Key: "LOGIN", Label: "User login", Placeholder: "login or email"},
					},
					Vars: map[string]string{"DB": current.Name, "ROLE": "portal"},
				})
			}
		case "y":
			if current, ok := m.current(); ok {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:      "tenant-user-create-operator",
					Description: "Create or update your operator account inside the selected database.",
					RelevantKeys: []string{
						"PROD_DB_NAME",
					},
					PromptFields: []event.PromptField{
						{Key: "LOGIN", Label: "Operator login", Placeholder: "me@example.com"},
						{Key: "NAME", Label: "Display name", Placeholder: "Tenant Operator"},
						{Key: "PASSWORD", Label: "Password", Placeholder: "password", Secret: true},
					},
					Vars: map[string]string{"DB": current.Name},
				})
			}
		case "i":
			if current, ok := m.current(); ok {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:      "tenant-user-role",
					Description: "Grant internal access to one user inside the selected database.",
					RelevantKeys: []string{
						"PROD_DB_NAME",
					},
					PromptFields: []event.PromptField{
						{Key: "LOGIN", Label: "User login", Placeholder: "login or email"},
					},
					Vars: map[string]string{"DB": current.Name, "ROLE": "internal"},
				})
			}
		case "c":
			if current, ok := m.current(); ok {
				return m, requestCmd(event.RequestMakeTargetMsg{
					Target:      "tenant-user-create-client",
					Description: "Create a fresh client user with portal access inside the selected database.",
					RelevantKeys: []string{
						"PROD_DB_NAME",
					},
					PromptFields: []event.PromptField{
						{Key: "LOGIN", Label: "Client login", Placeholder: "user@example.com"},
						{Key: "NAME", Label: "Display name", Placeholder: "Client User"},
						{Key: "PASSWORD", Label: "Initial password", Placeholder: "password", Secret: true},
					},
					Vars: map[string]string{"DB": current.Name},
				})
			}
		}
	}
	return m, nil
}

func (m Model) SetConfig(cfg *envconfig.Config) Model {
	m.cfg = cfg
	return m
}

func (m Model) SetSnapshot(snapshot state.Snapshot) Model {
	currentName := ""
	currentBackend := ""
	if current, ok := m.current(); ok {
		currentName = current.Name
		currentBackend = current.Backend
	}
	m.snapshot = snapshot
	if currentName != "" {
		for idx, item := range snapshot.Databases {
			if item.Name == currentName && item.Backend == currentBackend {
				m.selected = idx
				return m
			}
		}
	}
	if m.selected >= len(snapshot.Databases) {
		m.selected = max(0, len(snapshot.Databases)-1)
	}
	return m
}

func (m Model) MoveSelection(delta int) Model {
	if len(m.snapshot.Databases) == 0 || delta == 0 {
		return m
	}
	next := m.selected + delta
	if next < 0 {
		next = 0
	}
	if next >= len(m.snapshot.Databases) {
		next = len(m.snapshot.Databases) - 1
	}
	m.selected = next
	return m
}

func (m Model) Click(width, height, x, y int) (Model, bool) {
	if width <= 0 || height <= 0 || x < 0 || y < 0 {
		return m, false
	}
	leftWidth := max(54, (width*3)/5)
	if x >= leftWidth {
		return m, false
	}
	rowIndex := y - 3
	if rowIndex < 0 || rowIndex >= len(m.snapshot.Databases) {
		return m, false
	}
	m.selected = rowIndex
	return m, true
}

func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}
	leftWidth := max(54, (width*3)/5)
	rightWidth := max(28, width-leftWidth-4)
	left := panelStyle.Width(leftWidth).Height(max(10, height-4)).Render(m.listView(leftWidth - 4))
	right := panelStyle.Width(rightWidth).Height(max(10, height-4)).Render(m.detailView())
	return lipgloss.JoinHorizontal(lipgloss.Top, left, right)
}

func (m Model) listView(contentWidth int) string {
	lines := []string{
		titleStyle.Render("Databases"),
		headerRow(contentWidth),
	}
	for idx, item := range m.snapshot.Databases {
		prefix := " "
		style := lipgloss.NewStyle()
		if idx == m.selected {
			prefix = ">"
			style = selectedStyle
		}
		lines = append(lines, style.Render(fmt.Sprintf("%s %-18s %-7s %-10s %-10s %-12s %s",
			prefix,
			trim(item.Name, 18),
			trim(item.Backend, 7),
			trim(item.Owner, 10),
			trim(item.Size, 10),
			trim(item.Tags, 12),
			trim(item.Connectivity, 12),
		)))
	}
	if len(m.snapshot.Databases) == 0 {
		lines = append(lines, mutedStyle.Render("No database snapshot loaded."))
	}
	return strings.Join(lines, "\n")
}

func (m Model) detailView() string {
	item, ok := m.current()
	if !ok {
		return titleStyle.Render("Database Detail") + "\nNo database selected."
	}
	lines := []string{
		titleStyle.Render(item.Name),
		fmt.Sprintf("backend: %s", item.Backend),
		fmt.Sprintf("owner: %s", fallback(item.Owner, "n/a")),
		fmt.Sprintf("size: %s", fallback(item.Size, "n/a")),
		fmt.Sprintf("tags: %s", fallback(item.Tags, "n/a")),
		fmt.Sprintf("connectivity: %s", connectivityStyle(item.Connectivity).Render(item.Connectivity)),
		"",
		titleStyle.Render("Use In Modes"),
		strings.Join(item.CompatibleModes, ", "),
		"",
		titleStyle.Render("Primary Action"),
		fmt.Sprintf("make %s DB=%s", item.ActionTarget, item.Name),
		databaseActionHint(item.Backend),
	}
	lines = append(lines, "", titleStyle.Render("Quick Actions"))
	lines = append(lines, m.quickActionRows(item)...)
	if reason := m.blockedOpsReason(item); reason != "" {
		lines = append(lines, "", warnStyle.Render(reason))
	} else {
		lines = append(lines, "", titleStyle.Render("Tenant Ops"))
		lines = append(lines, mutedStyle.Render("Delete drops the database. Reset drops and recreates the tenant profile."))
	}
	if item.Alert != "" {
		lines = append(lines, "", warnStyle.Render("alert: "+item.Alert))
	}
	lines = append(lines, "", mutedStyle.Render("enter use this DB  |  click select  |  m manager  |  D delete  |  b/r local backup+restore  |  v validate"))
	return strings.Join(lines, "\n")
}

func (m Model) current() (state.DatabaseInfo, bool) {
	if len(m.snapshot.Databases) == 0 || m.selected < 0 || m.selected >= len(m.snapshot.Databases) {
		return state.DatabaseInfo{}, false
	}
	return m.snapshot.Databases[m.selected], true
}

func (m Model) useRequest() (event.RequestMakeTargetMsg, bool) {
	item, ok := m.current()
	if !ok || item.Name == "" {
		return event.RequestMakeTargetMsg{}, false
	}
	target := item.ActionTarget
	desc := "Run native Odoo with the selected database."
	relevant := []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"}
	if item.Backend == "local" {
		target = "dev-safe"
		desc = "Run native Odoo over local PostgreSQL with the selected database."
		relevant = []string{"DEV_HOST_HTTP_PORT", "PG_LOCAL_PORT"}
	}
	return event.RequestMakeTargetMsg{
		Target:       target,
		Description:  desc,
		RelevantKeys: relevant,
		Vars:         map[string]string{"DB": item.Name},
	}, true
}

func (m Model) dropRequest() (event.RequestMakeTargetMsg, bool) {
	item, ok := m.current()
	if !ok || item.Name == "" || m.blockedOpsReason(item) != "" {
		return event.RequestMakeTargetMsg{}, false
	}
	return event.RequestMakeTargetMsg{
		Target:            "db-drop",
		Description:       "Delete the selected database from the current PostgreSQL backend.",
		RelevantKeys:      []string{"PROD_DB_NAME"},
		RequireTypedCheck: true,
		ConfirmWord:       item.Name,
		Vars: map[string]string{
			"DB":         item.Name,
			"DB_BACKEND": item.Backend,
		},
	}, true
}

func (m Model) quickActionRows(item state.DatabaseInfo) []string {
	rows := []string{
		renderChipRow(
			chip(actionChipStyle, "enter open"),
			chip(neutralChipStyle, "m manager"),
			chip(neutralChipStyle, "v validate"),
		),
	}
	if reason := m.blockedOpsReason(item); reason != "" {
		rows = append(rows, renderChipRow(chip(blockedChipStyle, "tenant ops blocked")))
		return rows
	}
	rows = append(rows,
		renderChipRow(
			chip(actionChipStyle, "o bootstrap"),
			chip(neutralChipStyle, "a adjust"),
			chip(neutralChipStyle, "u users"),
		),
		renderChipRow(
			chip(neutralChipStyle, "p password"),
			chip(neutralChipStyle, "g portal"),
			chip(neutralChipStyle, "i internal"),
		),
		renderChipRow(
			chip(neutralChipStyle, "y operator"),
			chip(neutralChipStyle, "c client"),
			chip(dangerChipStyle, "x reset tenant"),
			chip(dangerChipStyle, "D delete db"),
		),
	)
	return rows
}

func (m Model) blockedOpsReason(item state.DatabaseInfo) string {
	switch item.Name {
	case "", "postgres":
		return "system database: tenant operations are unavailable"
	}
	if m.cfg != nil && item.Name == m.cfg.ProdDBName {
		return "primary database: reset/delete are blocked"
	}
	return ""
}

func databaseActionHint(backend string) string {
	if backend == "local" {
		return "Use local PostgreSQL via make dev-safe DB=<name>."
	}
	return "Use docker PostgreSQL via make dev DB=<name>."
}

func connectivityStyle(status string) lipgloss.Style {
	switch status {
	case "ok", "internal-only":
		return okStyle
	case "error", "unreachable":
		return errStyle
	default:
		return warnStyle
	}
}

func headerRow(contentWidth int) string {
	header := fmt.Sprintf("  %-18s %-7s %-10s %-10s %-12s %s", "name", "backend", "owner", "size", "tags", "connectivity")
	return mutedStyle.Render(trim(header, contentWidth))
}

func chip(style lipgloss.Style, label string) string {
	return style.Render(label)
}

func renderChipRow(chips ...string) string {
	return strings.Join(chips, " ")
}

func trim(value string, width int) string {
	if width <= 0 || len(value) <= width {
		return value
	}
	if width <= 3 {
		return value[:width]
	}
	return value[:width-3] + "..."
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
