package runtime

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/event"
	"github.com/kodoo/kodoo-tui/internal/state"
)

type modeSpec struct {
	Key          string
	Label        string
	Description  string
	Backend      string
	Prereq       string
	Ports        string
	Risk         string
	Primary      event.RequestMakeTargetMsg
	SecondaryTip string
}

type Model struct {
	snapshot state.Snapshot
	modes    []modeSpec
	selected int
	ready    bool
}

var (
	titleStyle    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	panelStyle    = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	selectedStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	mutedStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
	okStyle       = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
	warnStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
)

func New() Model {
	return Model{
		modes: []modeSpec{
			{
				Key:         "Stable Docker",
				Label:       "Stable Docker",
				Description: "Compose stack padrão para operação estável local.",
				Backend:     "docker compose",
				Prereq:      "DOMAIN, PROD_DB_* e configs geradas.",
				Ports:       "8069/8072 via nginx",
				Risk:        "Baixo. Mantém o stack estável.",
				Primary: event.RequestMakeTargetMsg{
					Target:      "up",
					Description: "Start the stable Docker stack with the public-sector runtime.",
					RelevantKeys: []string{
						"DOMAIN", "PROD_DB_NAME", "OLLAMA_MODEL",
					},
				},
				SecondaryTip: "Use Logs para incidentes e Config para regenerar arquivos.",
			},
			{
				Key:         "Stable Tunnel",
				Label:       "Stable Tunnel",
				Description: "Publica o ambiente via Cloudflare tunnel.",
				Backend:     "docker compose + cloudflared",
				Prereq:      "CLOUDFLARED_TOKEN e domínio válidos.",
				Ports:       "80/443 publicados pelo tunnel",
				Risk:        "Exposição pública. Verifique token e domínio.",
				Primary: event.RequestMakeTargetMsg{
					Target:      "up-tunnel",
					Description: "Start the public Cloudflare-published stack.",
					RelevantKeys: []string{
						"DOMAIN", "CLOUDFLARED_TOKEN",
					},
				},
				SecondaryTip: "Abra Dashboard para checar smoke público, tenant routing e exposição.",
			},
			{
				Key:         "Dev Host",
				Label:       "Dev Host",
				Description: "Roda Odoo nativo contra PostgreSQL local após escolher um DB.",
				Backend:     "processo local",
				Prereq:      "PG local acessível e DB cliente selecionável.",
				Ports:       "DEV_HOST_HTTP_PORT",
				Risk:        "Médio. Usa ambiente local e banco local.",
				Primary: event.RequestMakeTargetMsg{
					Target:          "dev-safe",
					Description:     "Run native Odoo over local PostgreSQL after choosing a client database.",
					RelevantKeys:    []string{"DEV_HOST_HTTP_PORT", "PG_LOCAL_PORT"},
					SelectDatabase:  true,
					DatabaseBackend: "local",
				},
				SecondaryTip: "Databases mostra os DBs locais compatíveis com esse modo.",
			},
			{
				Key:         "Dev Project",
				Label:       "Dev Project",
				Description: "Roda Odoo nativo contra o PostgreSQL do Docker após escolher um DB.",
				Backend:     "processo local + docker db",
				Prereq:      "Docker DB acessível e DB cliente selecionável.",
				Ports:       "DEV_PROJECT_HTTP_PORT",
				Risk:        "Médio. Usa processo local, mas compartilha o DB do projeto.",
				Primary: event.RequestMakeTargetMsg{
					Target:          "dev",
					Description:     "Run native Odoo over Docker PostgreSQL after choosing a client database.",
					RelevantKeys:    []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"},
					SelectDatabase:  true,
					DatabaseBackend: "docker",
				},
				SecondaryTip: "Use Logs para investigar boot local e Databases para trocar o cliente.",
			},
			{
				Key:         "Local Diagnostic / Manager",
				Label:       "Local Diagnostic / Manager",
				Description: "Diagnóstico rápido e abertura do database manager.",
				Backend:     "local tooling",
				Prereq:      "Host com Make targets disponíveis.",
				Ports:       "depende do target",
				Risk:        "Baixo. Não sobe stack completa.",
				Primary: event.RequestMakeTargetMsg{
					Target:      "doctor",
					Description: "Check host dependencies and prerequisites.",
					RelevantKeys: []string{
						"PG_LOCAL_PORT", "PG_LOCAL_HOST",
					},
				},
				SecondaryTip: "Use 'm' para abrir o database manager do backend docker.",
			},
			{
				Key:         "Stopped",
				Label:       "Stopped",
				Description: "Desliga o stack atual e limpa o contexto operacional.",
				Backend:     "docker compose",
				Prereq:      "Nenhum.",
				Ports:       "nenhum",
				Risk:        "Interrompe o stack estável atual.",
				Primary: event.RequestMakeTargetMsg{
					Target:            "down",
					Description:       "Stop the current Docker stack.",
					RelevantKeys:      []string{"DOMAIN"},
					RequireTypedCheck: true,
					ConfirmWord:       "sim",
				},
				SecondaryTip: "Use Dashboard para confirmar o estado parado após a ação.",
			},
		},
	}
}

func (m Model) Title() string {
	return "Runtime"
}

func (m Model) HelpLines() []string {
	return []string{
		"↑/↓ move between modes",
		"enter execute the primary action for the selected mode",
		"m open docker database manager from this screen",
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
			if m.selected < len(m.modes)-1 {
				m.selected++
			}
		case "enter":
			return m, requestCmd(m.modes[m.selected].Primary)
		case "m":
			return m, requestCmd(event.RequestMakeTargetMsg{
				Target:      "db-init",
				Description: "Open the Odoo database manager against Docker PostgreSQL.",
				RelevantKeys: []string{
					"DEV_PROJECT_DB",
				},
			})
		}
	}
	return m, nil
}

func (m Model) SetSnapshot(snapshot state.Snapshot) Model {
	currentKey := ""
	if m.selected >= 0 && m.selected < len(m.modes) {
		currentKey = m.modes[m.selected].Key
	}
	m.snapshot = snapshot
	if m.ready && currentKey != "" {
		for idx, mode := range m.modes {
			if mode.Key == currentKey {
				m.selected = idx
				return m
			}
		}
	}
	for idx, mode := range m.modes {
		if mode.Key == snapshot.Runtime.Mode {
			m.selected = idx
			m.ready = true
			break
		}
	}
	return m
}

func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}
	leftWidth := max(32, width/2)
	rightWidth := max(28, width-leftWidth-4)
	left := panelStyle.Width(leftWidth).Height(max(10, height-4)).Render(m.listView())
	right := panelStyle.Width(rightWidth).Height(max(10, height-4)).Render(m.detailView())
	return lipgloss.JoinHorizontal(lipgloss.Top, left, right)
}

func (m Model) listView() string {
	lines := []string{titleStyle.Render("Operational Modes")}
	for idx, mode := range m.modes {
		style := lipgloss.NewStyle()
		prefix := "  "
		if idx == m.selected {
			style = selectedStyle
			prefix = "> "
		}
		current := ""
		if mode.Key == m.snapshot.Runtime.Mode {
			current = okStyle.Render(" [current]")
		}
		lines = append(lines, style.Render(prefix+mode.Label)+current)
		lines = append(lines, mutedStyle.Render("  "+mode.Description))
	}
	return strings.Join(lines, "\n")
}

func (m Model) detailView() string {
	mode := m.modes[m.selected]
	lines := []string{
		titleStyle.Render(mode.Label),
		mode.Description,
		"",
		fmt.Sprintf("backend: %s", mode.Backend),
		fmt.Sprintf("prerequisites: %s", mode.Prereq),
		fmt.Sprintf("ports: %s", mode.Ports),
		fmt.Sprintf("risk: %s", mode.Risk),
		"",
		titleStyle.Render("Primary Action"),
		fmt.Sprintf("make %s", mode.Primary.Target),
		mode.Primary.Description,
		"",
		titleStyle.Render("Current Snapshot"),
		fmt.Sprintf("mode: %s", m.snapshot.Runtime.Mode),
		fmt.Sprintf("db: %s", fallback(m.snapshot.Runtime.ActiveDB, "not pinned")),
		fmt.Sprintf("next: %s", m.snapshot.Runtime.SuggestedNextStep),
		"",
		warnStyle.Render(mode.SecondaryTip),
	}
	return strings.Join(lines, "\n")
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
