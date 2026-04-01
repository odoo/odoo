package cockpit

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/event"
	"github.com/kodoo/kodoo-tui/internal/state"
)

type runtimeSpec struct {
	Key         string
	Label       string
	Description string
	Start       event.RequestMakeTargetMsg
	Bootstrap   event.RequestMakeTargetMsg
	Stop        event.RequestMakeTargetMsg
	Logs        event.RequestMakeTargetMsg
	Shell       event.RequestMakeTargetMsg
}

type Model struct {
	snapshot state.Snapshot
	specs    []runtimeSpec
	selected int
}

var (
	titleStyle    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	panelStyle    = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	selectedStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
	mutedStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
	okStyle       = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
	warnStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	errStyle      = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
)

func New() Model {
	return Model{
		specs: []runtimeSpec{
			{
				Key:         "studio",
				Label:       "Kodoo Studio Runtime",
				Description: "Odoo dedicado + forge_engine local para trabalhar no Kodoo Studio end-to-end.",
				Start: event.RequestMakeTargetMsg{
					Target:      "studio-runtime-up",
					Description: "Start the dedicated Kodoo Studio runtime and forge_engine.",
					RelevantKeys: []string{
						"STUDIO_RUNTIME_DB", "STUDIO_RUNTIME_HTTP_PORT", "STUDIO_RUNTIME_ENGINE_PORT", "STUDIO_RUNTIME_OUTPUT_PATH",
					},
				},
				Bootstrap: event.RequestMakeTargetMsg{
					Target:      "studio-runtime-bootstrap",
					Description: "Prepare the dedicated Studio database and install the Studio modules.",
					RelevantKeys: []string{
						"STUDIO_RUNTIME_DB", "STUDIO_RUNTIME_HTTP_PORT", "STUDIO_RUNTIME_ENGINE_PORT",
					},
				},
				Stop: event.RequestMakeTargetMsg{
					Target:      "studio-runtime-stop",
					Description: "Stop the dedicated Kodoo Studio runtime and forge_engine.",
					RelevantKeys: []string{
						"STUDIO_RUNTIME_DB", "STUDIO_RUNTIME_HTTP_PORT", "STUDIO_RUNTIME_ENGINE_PORT",
					},
				},
				Logs: event.RequestMakeTargetMsg{
					Target:      "studio-runtime-logs",
					Description: "Tail the dedicated Studio runtime logs.",
					RelevantKeys: []string{
						"STUDIO_RUNTIME_DB", "STUDIO_RUNTIME_HTTP_PORT", "STUDIO_RUNTIME_ENGINE_PORT",
					},
				},
				Shell: event.RequestMakeTargetMsg{
					Target:      "studio-runtime-shell",
					Description: "Open an Odoo shell against the dedicated Studio database.",
					RelevantKeys: []string{
						"STUDIO_RUNTIME_DB",
					},
					Interactive: false,
				},
			},
			{
				Key:         "gov",
				Label:       "Gov Suite Runtime",
				Description: "Odoo dedicado para validar fluxos e integrações da suíte gov com isolamento local.",
				Start: event.RequestMakeTargetMsg{
					Target:      "gov-runtime-up",
					Description: "Start the dedicated Gov suite runtime.",
					RelevantKeys: []string{
						"GOV_RUNTIME_DB", "GOV_RUNTIME_HTTP_PORT",
					},
				},
				Bootstrap: event.RequestMakeTargetMsg{
					Target:      "gov-runtime-bootstrap",
					Description: "Prepare the dedicated Gov suite database and install gov_suite.",
					RelevantKeys: []string{
						"GOV_RUNTIME_DB", "GOV_RUNTIME_HTTP_PORT",
					},
				},
				Stop: event.RequestMakeTargetMsg{
					Target:      "gov-runtime-stop",
					Description: "Stop the dedicated Gov suite runtime.",
					RelevantKeys: []string{
						"GOV_RUNTIME_DB", "GOV_RUNTIME_HTTP_PORT",
					},
				},
				Logs: event.RequestMakeTargetMsg{
					Target:      "gov-runtime-logs",
					Description: "Tail the dedicated Gov suite log.",
					RelevantKeys: []string{
						"GOV_RUNTIME_DB", "GOV_RUNTIME_HTTP_PORT",
					},
				},
				Shell: event.RequestMakeTargetMsg{
					Target:      "gov-runtime-shell",
					Description: "Open an Odoo shell against the dedicated Gov suite database.",
					RelevantKeys: []string{
						"GOV_RUNTIME_DB",
					},
				},
			},
		},
	}
}

func (m Model) Title() string {
	return "Cockpit"
}

func (m Model) HelpLines() []string {
	return []string{
		"↑/↓ move between dedicated runtimes",
		"enter or u start the selected runtime",
		"b bootstrap/update modules for the selected runtime",
		"s stop the selected runtime",
		"l tail logs for the selected runtime",
		"o open the Odoo shell for the selected runtime",
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
			if m.selected < len(m.specs)-1 {
				m.selected++
			}
		case "enter", "u":
			return m, requestCmd(m.specs[m.selected].Start)
		case "b":
			return m, requestCmd(m.specs[m.selected].Bootstrap)
		case "s":
			return m, requestCmd(m.specs[m.selected].Stop)
		case "l":
			return m, requestCmd(m.specs[m.selected].Logs)
		case "o":
			return m, requestCmd(m.specs[m.selected].Shell)
		}
	}
	return m, nil
}

func (m Model) SetSnapshot(snapshot state.Snapshot) Model {
	currentKey := ""
	if m.selected >= 0 && m.selected < len(m.specs) {
		currentKey = m.specs[m.selected].Key
	}
	m.snapshot = snapshot
	if currentKey == "" {
		return m
	}
	for idx, spec := range m.specs {
		if spec.Key == currentKey {
			m.selected = idx
			break
		}
	}
	return m
}

func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}
	leftWidth := max(34, width/2)
	rightWidth := max(36, width-leftWidth-4)
	left := panelStyle.Width(leftWidth).Height(max(10, height-4)).Render(m.listView())
	right := panelStyle.Width(rightWidth).Height(max(10, height-4)).Render(m.detailView())
	return lipgloss.JoinHorizontal(lipgloss.Top, left, right)
}

func (m Model) listView() string {
	lines := []string{titleStyle.Render("Dedicated Runtime Cockpit")}
	for idx, spec := range m.specs {
		style := lipgloss.NewStyle()
		prefix := "  "
		if idx == m.selected {
			style = selectedStyle
			prefix = "> "
		}
		runtime := m.runtimeState(spec.Key)
		lines = append(lines, style.Render(prefix+spec.Label)+" "+statusBadge(runtime.Status))
		lines = append(lines, mutedStyle.Render("  "+fallback(runtime.Detail, spec.Description)))
		if runtime.LocalURL != "" {
			lines = append(lines, mutedStyle.Render("  "+runtime.LocalURL))
		}
	}
	return strings.Join(lines, "\n")
}

func (m Model) detailView() string {
	spec := m.specs[m.selected]
	runtime := m.runtimeState(spec.Key)
	lines := []string{
		titleStyle.Render(spec.Label),
		fallback(runtime.Description, spec.Description),
		"",
		fmt.Sprintf("status: %s", runtime.Status),
		fmt.Sprintf("odoo pid: %s", fallback(runtime.OdooPIDStatus, "stopped")),
		fmt.Sprintf("database: %s", fallback(runtime.DBName, "n/a")),
		fmt.Sprintf("local url: %s", fallback(runtime.LocalURL, "n/a")),
		fmt.Sprintf("config: %s", fallback(runtime.ConfigPath, "n/a")),
		fmt.Sprintf("modules: %s", fallback(runtime.Modules, "n/a")),
	}
	if runtime.EngineURL != "" {
		lines = append(lines, fmt.Sprintf("engine url: %s", runtime.EngineURL))
		lines = append(lines, fmt.Sprintf("engine pid: %s", fallback(runtime.EnginePIDStatus, "stopped")))
	}
	if runtime.OutputPath != "" {
		lines = append(lines, fmt.Sprintf("output path: %s", runtime.OutputPath))
	}

	lines = append(lines, "", titleStyle.Render("Actions"))
	lines = append(lines,
		"enter/u  start runtime",
		"b        bootstrap or refresh modules",
		"s        stop runtime",
		"l        tail logs",
		"o        open Odoo shell",
	)

	lines = append(lines, "", titleStyle.Render("Warnings"))
	if len(runtime.Warnings) == 0 {
		lines = append(lines, okStyle.Render("Runtime looks healthy."))
	} else {
		for _, warning := range runtime.Warnings {
			lines = append(lines, warnStyle.Render("- "+warning))
		}
	}
	return strings.Join(lines, "\n")
}

func (m Model) runtimeState(key string) state.DedicatedRuntimeState {
	for _, runtime := range m.snapshot.DedicatedRuntimes {
		if runtime.Key == key {
			return runtime
		}
	}
	for _, spec := range m.specs {
		if spec.Key == key {
			return state.DedicatedRuntimeState{
				Key:         spec.Key,
				Label:       spec.Label,
				Description: spec.Description,
				Status:      "unknown",
				Detail:      "snapshot ainda não carregou este runtime",
			}
		}
	}
	return state.DedicatedRuntimeState{}
}

func requestCmd(req event.RequestMakeTargetMsg) tea.Cmd {
	return func() tea.Msg { return req }
}

func statusBadge(status string) string {
	switch status {
	case "running":
		return okStyle.Render("[running]")
	case "degraded":
		return warnStyle.Render("[degraded]")
	case "stopped":
		return mutedStyle.Render("[stopped]")
	default:
		return errStyle.Render("[" + fallback(status, "unknown") + "]")
	}
}

func fallback(value, defaultValue string) string {
	if strings.TrimSpace(value) == "" {
		return defaultValue
	}
	return value
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
