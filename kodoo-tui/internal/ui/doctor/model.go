package doctor

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/kodoo/kodoo-tui/internal/event"
	"github.com/kodoo/kodoo-tui/internal/state"
)

type doctorCase struct {
	Severity state.Severity
	Title    string
	Symptom  string
	Cause    string
	Fix      string
	Current  bool
}

type modeDoctor struct {
	Key          string
	Label        string
	Description  string
	Primary      event.RequestMakeTargetMsg
	Cases        []doctorCase
	CurrentIssue string
}

type Model struct {
	snapshot state.Snapshot
	modes    []modeDoctor
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
	errStyle      = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
)

func New() Model {
	return Model{
		modes: buildModeDoctors(state.Snapshot{}),
	}
}

func (m Model) Title() string {
	return "Doctor"
}

func (m Model) HelpLines() []string {
	return []string{
		"↑/↓ move between stack doctor modes",
		"enter run the suggested primary action for the selected mode",
		"r refresh the global snapshot",
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
			if len(m.modes) == 0 {
				return m, nil
			}
			return m, requestCmd(m.modes[m.selected].Primary)
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
	m.modes = buildModeDoctors(snapshot)
	if m.ready && currentKey != "" {
		for idx, mode := range m.modes {
			if mode.Key == currentKey {
				m.selected = idx
				return m
			}
		}
	}
	m.selected = preferredModeIndex(m.modes, snapshot.Runtime.Mode)
	m.ready = true
	return m
}

func (m Model) View(width, height int) string {
	if width <= 0 || height <= 0 {
		return ""
	}

	leftWidth := max(34, width/3)
	rightWidth := max(32, width-leftWidth-4)
	left := panelStyle.Width(leftWidth).Height(max(10, height-4)).Render(m.listView())
	right := panelStyle.Width(rightWidth).Height(max(10, height-4)).Render(m.detailView())
	return lipgloss.JoinHorizontal(lipgloss.Top, left, right)
}

func (m Model) listView() string {
	lines := []string{
		titleStyle.Render("Doctor Modes"),
		mutedStyle.Render("Diagnostico guiado por modalidade de stack."),
	}
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
		lines = append(lines, "", style.Render(prefix+mode.Label)+current)
		lines = append(lines, mutedStyle.Render("  "+mode.Description))
		if strings.TrimSpace(mode.CurrentIssue) != "" {
			lines = append(lines, warnStyle.Render("  now: "+mode.CurrentIssue))
		} else {
			lines = append(lines, mutedStyle.Render(fmt.Sprintf("  %d common checks", len(mode.Cases))))
		}
	}
	return strings.Join(lines, "\n")
}

func (m Model) detailView() string {
	if len(m.modes) == 0 {
		return titleStyle.Render("Doctor") + "\n" + mutedStyle.Render("No doctor data available.")
	}

	mode := m.modes[m.selected]
	lines := []string{
		titleStyle.Render(mode.Label),
		mode.Description,
		"",
		titleStyle.Render("Primary Action"),
		fmt.Sprintf("make %s", mode.Primary.Target),
		mode.Primary.Description,
	}

	if strings.TrimSpace(mode.CurrentIssue) != "" {
		lines = append(lines, "", titleStyle.Render("Current Focus"), warnStyle.Render(mode.CurrentIssue))
	}

	lines = append(lines, "", titleStyle.Render("Cases"))
	for idx, item := range mode.Cases {
		lines = append(lines, "")
		lines = append(lines, fmt.Sprintf("%s %s", severityDot(item.Severity), item.Title))
		if item.Current {
			lines = append(lines, warnStyle.Render("current environment example"))
		}
		lines = append(lines, "symptom: "+item.Symptom)
		lines = append(lines, mutedStyle.Render("cause: "+item.Cause))
		lines = append(lines, warnStyle.Render("fix: "+item.Fix))
		if idx >= 3 {
			break
		}
	}
	return strings.Join(lines, "\n")
}

func buildModeDoctors(snapshot state.Snapshot) []modeDoctor {
	return []modeDoctor{
		{
			Key:         "Stable Tunnel",
			Label:       "Stable Tunnel Doctor",
			Description: "Publicacao via Cloudflare Tunnel e nginx interno.",
			Primary: event.RequestMakeTargetMsg{
				Target:      "up-tunnel",
				Description: "Start the public Cloudflare-published stack.",
				RelevantKeys: []string{
					"DOMAIN", "CLOUDFLARED_TOKEN",
				},
			},
			Cases:        stableTunnelCases(snapshot),
			CurrentIssue: currentIssue(stableTunnelCases(snapshot)),
		},
		{
			Key:         "Stable Docker",
			Label:       "Stable Docker Doctor",
			Description: "Stack estavel local com compose, Odoo, nginx e banco Docker.",
			Primary: event.RequestMakeTargetMsg{
				Target:      "up",
				Description: "Start the stable Docker stack with the public-sector runtime.",
				RelevantKeys: []string{
					"DOMAIN", "PROD_DB_NAME", "OLLAMA_MODEL",
				},
			},
			Cases:        stableDockerCases(snapshot),
			CurrentIssue: currentIssue(stableDockerCases(snapshot)),
		},
		{
			Key:         "Dev Host",
			Label:       "Dev Host Doctor",
			Description: "Odoo nativo contra PostgreSQL local.",
			Primary: event.RequestMakeTargetMsg{
				Target:          "dev-safe",
				Description:     "Run native Odoo over local PostgreSQL after choosing a client database.",
				RelevantKeys:    []string{"DEV_HOST_HTTP_PORT", "PG_LOCAL_PORT"},
				SelectDatabase:  true,
				DatabaseBackend: "local",
			},
			Cases:        devHostCases(snapshot),
			CurrentIssue: currentIssue(devHostCases(snapshot)),
		},
		{
			Key:         "Dev Project",
			Label:       "Dev Project Doctor",
			Description: "Odoo nativo contra o PostgreSQL exposto pelo stack Docker.",
			Primary: event.RequestMakeTargetMsg{
				Target:          "dev",
				Description:     "Run native Odoo over Docker PostgreSQL after choosing a client database.",
				RelevantKeys:    []string{"DEV_PROJECT_HTTP_PORT", "DOCKER_DB_HOST_PORT"},
				SelectDatabase:  true,
				DatabaseBackend: "docker",
			},
			Cases:        devProjectCases(snapshot),
			CurrentIssue: currentIssue(devProjectCases(snapshot)),
		},
		{
			Key:         "Local Diagnostic / Manager",
			Label:       "Local Diagnostic Doctor",
			Description: "Checagens de host, configuracao e database manager.",
			Primary: event.RequestMakeTargetMsg{
				Target:      "doctor",
				Description: "Check host dependencies and prerequisites.",
				RelevantKeys: []string{
					"PG_LOCAL_PORT", "PG_LOCAL_HOST",
				},
			},
			Cases:        localDiagnosticCases(snapshot),
			CurrentIssue: currentIssue(localDiagnosticCases(snapshot)),
		},
	}
}

func stableTunnelCases(snapshot state.Snapshot) []doctorCase {
	cases := []doctorCase{}

	cloudflared := serviceStatus(snapshot.Services, "kodoo-cloudflared")
	nginx := serviceStatus(snapshot.Services, "kodoo-nginx")
	odoo := serviceStatus(snapshot.Services, "kodoo-odoo")

	if hasIncident(snapshot.Incidents, "Tunnel sem token") || (!cloudflared.running && odoo.running) {
		cause := "O tunnel nao sobe, entao o dominio publico nunca chega ao nginx."
		if hasIncident(snapshot.Incidents, "Tunnel sem token") {
			cause = "CLOUDFLARED_TOKEN esta vazio e o compose nem consegue iniciar o container do tunnel."
		}
		cases = append(cases, doctorCase{
			Severity: state.SeverityCritical,
			Title:    "Cloudflare nao publica o ambiente atual",
			Symptom:  fmt.Sprintf("cloudflared=%s, nginx=%s, odoo=%s, publico indisponivel", cloudflared.status, nginx.status, odoo.status),
			Cause:    cause,
			Fix:      "Preencha CLOUDFLARED_TOKEN, valide o Public Hostname no Zero Trust e rode make up-tunnel.",
			Current:  true,
		})
	}
	if hasIncident(snapshot.Incidents, "Apex DNS ausente no edge") {
		cases = append(cases, doctorCase{
			Severity: state.SeverityCritical,
			Title:    "Apex do dominio nao foi publicado",
			Symptom:  "www responde, mas o dominio raiz continua indisponivel no navegador e no smoke publico.",
			Cause:    "O edge conhece www.<dominio>, mas o hostname apex ainda nao foi criado no Cloudflare/Tunnel.",
			Fix:      "Adicionar o Public Hostname do apex no Cloudflare e manter www apenas como redirect para o dominio raiz.",
			Current:  true,
		})
	}

	cases = append(cases,
		doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Nginx do tunnel nao sobe por conflito na porta 80",
			Symptom:  "make up-tunnel falha com bind address already in use em 0.0.0.0:80.",
			Cause:    "Outro servico do host ja esta ouvindo na porta 80, entao o container kodoo-nginx nao consegue publicar HTTP.",
			Fix:      "Liberar a porta 80 no host ou ajustar a exposicao publica antes de repetir make up-tunnel.",
		},
		doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Tunnel sobe, mas dominio retorna erro",
			Symptom:  "cloudflared running, porem o acesso publico cai em 502/1033/connection refused.",
			Cause:    "Hostname do tunnel aponta para destino incorreto ou nginx nao esta acessivel em http://nginx:80.",
			Fix:      "Conferir Public Hostname no Cloudflare Zero Trust e validar o servico nginx no compose tunnel.",
		},
		doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Cloudflared fica em Created ou restart loop",
			Symptom:  "o container nao entra em running ou reinicia logo apos subir.",
			Cause:    "Token invalido, expirado ou stack iniciada sem as variaveis exigidas.",
			Fix:      "Regerar o token do tunnel, atualizar .env e revisar logs de cloudflared.",
		},
		doctorCase{
			Severity: state.SeverityInfo,
			Title:    "Publico abre, mas Odoo interno responde mal",
			Symptom:  "o dominio resolve, mas login/websocket/upload falham de forma intermitente.",
			Cause:    "nginx ou odoo nao estao saudaveis, embora o tunnel esteja ativo.",
			Fix:      "Checar smoke local/publico, logs de nginx/odoo e estabilizar o runtime antes de culpar o tunnel.",
		},
	)
	return cases
}

func stableDockerCases(snapshot state.Snapshot) []doctorCase {
	cases := []doctorCase{}
	odoo := serviceStatus(snapshot.Services, "kodoo-odoo")
	db := serviceStatus(snapshot.Services, "db-docker")

	if !odoo.running || !db.running {
		cases = append(cases, doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Stack estavel parcial ou parado",
			Symptom:  fmt.Sprintf("odoo=%s, db-docker=%s", odoo.status, db.status),
			Cause:    "Algum servico base do compose nao esta operacional.",
			Fix:      "Subir o modo Stable Docker e abrir Logs para o primeiro erro de bootstrap.",
			Current:  snapshot.Runtime.Mode == "Stable Docker" || snapshot.Runtime.Mode == "Stopped",
		})
	}

	cases = append(cases,
		doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Odoo sobe, mas nginx nao publica",
			Symptom:  "container do Odoo em running, porem a URL local nao responde pelo proxy.",
			Cause:    "nginx parado, configuracao gerada ausente ou mismatch de porta upstream.",
			Fix:      "Regenerar configs, validar nginx e repetir smoke local.",
		},
		doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Banco Docker nao responde",
			Symptom:  "odoo falha no startup ou Databases mostra backend docker unreachable.",
			Cause:    "postgres do compose ainda nao subiu, bind port mudou ou healthcheck ainda esta vermelho.",
			Fix:      "Validar servico db e aguardar healthy antes de reiniciar o Odoo.",
		},
		doctorCase{
			Severity: state.SeverityInfo,
			Title:    "Smoke falha com stack em running",
			Symptom:  "containers estao up, mas smoke local retorna erro HTTP ou timeout.",
			Cause:    "aplicacao ainda bootando, banco inconsistente ou erro funcional no Odoo.",
			Fix:      "Abrir Logs, localizar o primeiro traceback e so depois repetir smoke.",
		},
	)
	return cases
}

func devHostCases(snapshot state.Snapshot) []doctorCase {
	cases := []doctorCase{}
	localDB := serviceStatus(snapshot.Services, "db-local")
	devHost := serviceStatus(snapshot.Services, "odoo-dev-host")

	if !localDB.running || strings.Contains(devHost.status, "stale") {
		cases = append(cases, doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Dev Host bloqueado por PostgreSQL local ou PID stale",
			Symptom:  fmt.Sprintf("db-local=%s, odoo-dev-host=%s", localDB.status, devHost.status),
			Cause:    "O processo local depende do PostgreSQL do host e de um ciclo limpo de PID.",
			Fix:      "Restaurar conectividade do PostgreSQL local, limpar PID velho e subir dev-safe de novo.",
			Current:  snapshot.Runtime.Mode == "Dev Host",
		})
	}

	cases = append(cases,
		doctorCase{
			Severity: state.SeverityWarning,
			Title:    "DB local existe, mas o database escolhido nao abre",
			Symptom:  "processo inicia e cai ao carregar um cliente especifico.",
			Cause:    "banco local ausente, owner incorreto ou modulo instalado quebrou o bootstrap.",
			Fix:      "Trocar de banco em Databases e comparar o primeiro traceback do boot.",
		},
		doctorCase{
			Severity: state.SeverityInfo,
			Title:    "Porta do Dev Host ocupada",
			Symptom:  "o processo local sobe parcialmente e morre com bind error.",
			Cause:    "DEV_HOST_HTTP_PORT esta em uso por outro processo.",
			Fix:      "Liberar a porta configurada ou ajustar DEV_HOST_HTTP_PORT na Config.",
		},
	)
	return cases
}

func devProjectCases(snapshot state.Snapshot) []doctorCase {
	cases := []doctorCase{}
	dockerDB := serviceStatus(snapshot.Services, "db-docker")
	devProject := serviceStatus(snapshot.Services, "odoo-dev-project")

	if !dockerDB.running || strings.Contains(devProject.status, "stale") {
		cases = append(cases, doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Dev Project bloqueado por Docker DB ou PID stale",
			Symptom:  fmt.Sprintf("db-docker=%s, odoo-dev-project=%s", dockerDB.status, devProject.status),
			Cause:    "O processo local depende da porta exposta pelo postgres do compose e de PID coerente.",
			Fix:      "Subir o stack de banco Docker, limpar PID antigo e repetir dev.",
			Current:  snapshot.Runtime.Mode == "Dev Project",
		})
	}

	cases = append(cases,
		doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Banco Docker compartilhado conflita com trabalho local",
			Symptom:  "troca de banco ou restart no stack derruba o fluxo de desenvolvimento.",
			Cause:    "o modo usa o postgres compartilhado do projeto, nao um backend local isolado.",
			Fix:      "Quando quiser isolamento, migrar para Dev Host ou manter o DB Docker estavel.",
		},
		doctorCase{
			Severity: state.SeverityInfo,
			Title:    "Modo dev sobe, mas URL local nao responde",
			Symptom:  "PID existe, porem a porta HTTP configurada nao aceita conexao.",
			Cause:    "falha de bind, crash no startup ou processo travado antes do servidor HTTP.",
			Fix:      "Ler logs do processo local e validar DEV_PROJECT_HTTP_PORT.",
		},
	)
	return cases
}

func localDiagnosticCases(snapshot state.Snapshot) []doctorCase {
	cases := []doctorCase{}

	if !snapshot.Config.EnvExists || len(snapshot.Config.MissingKeys) > 0 {
		cases = append(cases, doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Configuracao base incompleta",
			Symptom:  fmt.Sprintf(".env=%t, missing=%d", snapshot.Config.EnvExists, len(snapshot.Config.MissingKeys)),
			Cause:    "Sem configuracao minima, varios modos vao falhar antes mesmo de subir servicos.",
			Fix:      "Abrir Config, preencher as chaves obrigatorias e regenerar os arquivos de deploy.",
			Current:  true,
		})
	}
	if snapshot.Config.UsesLegacyFile {
		cases = append(cases, doctorCase{
			Severity: state.SeverityCritical,
			Title:    "Configuracao salva apenas em .env.make",
			Symptom:  fmt.Sprintf("env path atual=%s", snapshot.Config.EnvPath),
			Cause:    "A TUI estava operando com o arquivo legado, mas o docker compose espera .env.",
			Fix:      "Reabra a TUI para migracao automatica ou edite/salve a configuracao para promover o legado para .env.",
			Current:  true,
		})
	}

	cases = append(cases,
		doctorCase{
			Severity: state.SeverityWarning,
			Title:    "Arquivos gerados de Odoo ausentes",
			Symptom:  "o compose ou os modos nativos usam configs ainda nao renderizadas.",
			Cause:    "prod/dev-host/dev-project configs nao foram geradas apos alterar .env.",
			Fix:      "Executar as acoes de generate na aba Config ou rodar refresh-safe.",
		},
		doctorCase{
			Severity: state.SeverityInfo,
			Title:    "Doctor do host passa, mas stack continua quebrando",
			Symptom:  "dependencias locais estao ok, porem o problema persiste em runtime especifico.",
			Cause:    "o defeito esta na modalidade da stack, nao no host genericamente.",
			Fix:      "Trocar para o doctor da modalidade correta e seguir o caso de erro dominante.",
		},
	)
	return cases
}

type serviceSnapshot struct {
	status  string
	running bool
}

func serviceStatus(services []state.ServiceHealth, name string) serviceSnapshot {
	for _, service := range services {
		if service.Name != name {
			continue
		}
		return serviceSnapshot{
			status:  service.Status,
			running: service.Level != state.SeverityCritical && !strings.Contains(strings.ToLower(service.Status), "not running"),
		}
	}
	return serviceSnapshot{status: "unknown", running: false}
}

func hasIncident(incidents []state.Incident, summary string) bool {
	for _, incident := range incidents {
		if incident.Summary == summary {
			return true
		}
	}
	return false
}

func currentIssue(cases []doctorCase) string {
	for _, item := range cases {
		if item.Current {
			return item.Title
		}
	}
	return ""
}

func preferredModeIndex(modes []modeDoctor, runtimeMode string) int {
	for idx, mode := range modes {
		if mode.CurrentIssue != "" {
			return idx
		}
		if mode.Key == runtimeMode {
			return idx
		}
	}
	return 0
}

func severityDot(level state.Severity) string {
	switch level {
	case state.SeverityCritical:
		return errStyle.Render("●")
	case state.SeverityWarning:
		return warnStyle.Render("●")
	default:
		return okStyle.Render("●")
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
