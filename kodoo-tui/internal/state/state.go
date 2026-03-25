package state

import (
	"context"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/kodoo/kodoo-tui/internal/database"
	"github.com/kodoo/kodoo-tui/internal/docker"
	"github.com/kodoo/kodoo-tui/internal/envconfig"
	"github.com/kodoo/kodoo-tui/internal/health"
)

type Severity string

const (
	SeverityCritical Severity = "critical"
	SeverityWarning  Severity = "warning"
	SeverityInfo     Severity = "info"
)

type ServiceHealth struct {
	Name   string
	Status string
	Detail string
	Level  Severity
}

type DatabaseInfo struct {
	Name            string
	Backend         string
	Owner           string
	Size            string
	Tags            string
	Connectivity    string
	CompatibleModes []string
	ActionTarget    string
	Alert           string
}

type Incident struct {
	Severity   Severity
	Summary    string
	Cause      string
	Suggestion string
}

type ConfigState struct {
	EnvPath        string
	EnvExists      bool
	UsesLegacyFile bool
	GeneratedFiles map[string]bool
	MissingKeys    []string
	ProdListDB     bool
	ProdDBFilter   string
}

type RuntimeState struct {
	Mode              string
	RuntimeProfile    string
	Backend           string
	DBBackend         string
	LocalPIDStatus    string
	LocalURL          string
	PublicURL         string
	ConfigStatus      string
	Warnings          []string
	PortSummary       string
	ActiveDB          string
	LastRefresh       time.Time
	LastIncident      string
	SuggestedNextStep string
}

type Snapshot struct {
	Runtime      RuntimeState
	Services     []ServiceHealth
	Databases    []DatabaseInfo
	Incidents    []Incident
	Smoke        []health.CheckResult
	Containers   []docker.Container
	Stats        []docker.Stat
	Logs         []string
	ServiceNames []string
	Config       ConfigState
}

type MsgSnapshotLoaded struct {
	Snapshot Snapshot
	Err      error
}

func RefreshCmd(cfg *envconfig.Config, repoDir, activeDB string) tea.Cmd {
	return func() tea.Msg {
		snapshot, err := Load(context.Background(), cfg, repoDir, activeDB)
		return MsgSnapshotLoaded{Snapshot: snapshot, Err: err}
	}
}

func Load(ctx context.Context, cfg *envconfig.Config, repoDir, activeDB string) (Snapshot, error) {
	snapshot := Snapshot{
		Config: ConfigState{
			EnvPath:        cfg.Path,
			EnvExists:      cfg.Exists,
			UsesLegacyFile: filepath.Base(cfg.Path) == envconfig.LegacyEnvFile,
			GeneratedFiles: map[string]bool{
				"deploy/odoo/kodoo.prod.local.conf":        fileExists(filepath.Join(repoDir, "deploy/odoo/kodoo.prod.local.conf")),
				"deploy/odoo/kodoo.dev-host.local.conf":    fileExists(filepath.Join(repoDir, "deploy/odoo/kodoo.dev-host.local.conf")),
				"deploy/odoo/kodoo.dev-project.local.conf": fileExists(filepath.Join(repoDir, "deploy/odoo/kodoo.dev-project.local.conf")),
			},
			MissingKeys:  missingConfigKeys(cfg),
			ProdListDB:   cfg.ProdListDB,
			ProdDBFilter: cfg.ProdDBFilter,
		},
	}

	containers, containerErr := docker.ListContainers()
	if containerErr != nil {
		return snapshot, containerErr
	}
	stats, _ := docker.Stats()
	logLines, _ := docker.TailLogs(cfg.TUILogLines, "todos")
	services, _ := docker.Services()
	smoke := health.SmokeAll(cfg)

	localDBOK := portReachable(cfg.PGLocalHost, cfg.PGLocalPort)
	dockerDBHostPortOK := portReachable(cfg.DockerDBBindHost, cfg.DockerDBHostPort)
	devHostPID := readPIDStatus(filepath.Join(repoDir, "logs", "odoo-dev-host.pid"))
	devProjectPID := readPIDStatus(filepath.Join(repoDir, "logs", "odoo-dev-project.pid"))
	dockerDBRunning := containerRunning(containers, "kodoo-db")

	snapshot.Containers = containers
	snapshot.Stats = stats
	snapshot.Logs = logLines
	snapshot.ServiceNames = services
	snapshot.Smoke = smoke
	snapshot.Runtime = buildRuntimeState(cfg, containers, smoke, snapshot.Config, devHostPID, devProjectPID, activeDB)
	snapshot.Databases = loadDatabases(ctx, repoDir, snapshot.Runtime.Mode, localDBOK, dockerDBHostPortOK, dockerDBRunning)
	snapshot.Services = buildServices(containers, snapshot.Runtime.Mode, localDBOK, dockerDBHostPortOK, dockerDBRunning, cfg, devHostPID, devProjectPID)
	snapshot.Incidents = detectIncidents(cfg, snapshot, localDBOK, dockerDBHostPortOK, dockerDBRunning, devHostPID, devProjectPID)

	if len(snapshot.Incidents) > 0 {
		snapshot.Runtime.LastIncident = snapshot.Incidents[0].Summary
		snapshot.Runtime.SuggestedNextStep = snapshot.Incidents[0].Suggestion
	} else {
		snapshot.Runtime.LastIncident = "Nenhum incidente ativo"
		snapshot.Runtime.SuggestedNextStep = defaultNextStep(snapshot.Runtime.Mode)
	}
	if !cfg.Exists {
		snapshot.Runtime.ConfigStatus = ".env ausente"
	} else if len(snapshot.Config.MissingKeys) > 0 {
		snapshot.Runtime.ConfigStatus = "config incompleta"
	} else {
		snapshot.Runtime.ConfigStatus = "config pronta"
	}
	return snapshot, nil
}

func buildRuntimeState(cfg *envconfig.Config, containers []docker.Container, smoke []health.CheckResult, config ConfigState, devHostPID, devProjectPID pidStatus, activeDB string) RuntimeState {
	mode, backend, dbBackend := detectMode(containers, devHostPID, devProjectPID)
	warnings := make([]string, 0, 4)
	for _, result := range smoke {
		if !result.OK {
			warnings = append(warnings, fmt.Sprintf("%s failed", result.Name))
		}
	}
	if len(config.MissingKeys) > 0 {
		warnings = append(warnings, fmt.Sprintf("%d required config values missing", len(config.MissingKeys)))
	}
	return RuntimeState{
		Mode:           mode,
		RuntimeProfile: runtimeProfile(containers),
		Backend:        backend,
		DBBackend:      dbBackend,
		LocalPIDStatus: localPIDSummary(devHostPID, devProjectPID),
		LocalURL:       cfg.LocalHTTPURL(),
		PublicURL:      cfg.PublicHTTPURL(),
		Warnings:       warnings,
		PortSummary:    portSummary(containers),
		ActiveDB:       activeDB,
		LastRefresh:    time.Now(),
	}
}

func buildServices(containers []docker.Container, mode string, localDBOK, dockerDBHostPortOK, dockerDBRunning bool, cfg *envconfig.Config, devHostPID, devProjectPID pidStatus) []ServiceHealth {
	services := []ServiceHealth{
		serviceFromPort("db-local", localDBOK, "postgres local", "127.0.0.1 reachability"),
		serviceFromDockerDB(mode, dockerDBRunning, dockerDBHostPortOK, cfg.DockerDBBindHost, cfg.DockerDBHostPort),
	}

	for _, name := range []string{"kodoo-odoo", "kodoo-nginx", "kodoo-cloudflared", "kodoo-ollama"} {
		services = append(services, serviceFromContainer(name, containers))
	}
	services = append(services, serviceFromPID("odoo-dev-host", devHostPID))
	services = append(services, serviceFromPID("odoo-dev-project", devProjectPID))
	return services
}

func loadDatabases(ctx context.Context, repoDir, mode string, localDBOK, dockerDBHostPortOK, dockerDBRunning bool) []DatabaseInfo {
	var rows []DatabaseInfo
	for _, backend := range []string{"docker", "local"} {
		records, err := database.List(ctx, repoDir, backend)
		if err != nil {
			rows = append(rows, DatabaseInfo{
				Name:         fmt.Sprintf("%s backend", backend),
				Backend:      backend,
				Connectivity: "error",
				Alert:        err.Error(),
			})
			continue
		}
		for _, record := range records {
			info := DatabaseInfo{
				Name:            record.Name,
				Backend:         record.Backend,
				Owner:           record.Owner,
				Size:            record.Size,
				Tags:            record.Tags,
				CompatibleModes: compatibleModes(record.Backend),
				ActionTarget:    preferredDBAction(record.Backend),
				Connectivity:    connectivityLabel(record.Backend, mode, localDBOK, dockerDBHostPortOK, dockerDBRunning),
			}
			if info.Connectivity == "container-only" {
				info.Alert = "Docker DB is reachable through the container, but the host bind port is closed."
			} else if info.Connectivity != "ok" && info.Connectivity != "internal-only" {
				info.Alert = fmt.Sprintf("%s backend is not reachable", record.Backend)
			}
			rows = append(rows, info)
		}
	}
	slices.SortFunc(rows, func(a, b DatabaseInfo) int {
		if a.Backend == b.Backend {
			return strings.Compare(a.Name, b.Name)
		}
		return strings.Compare(a.Backend, b.Backend)
	})
	return rows
}

func detectIncidents(cfg *envconfig.Config, snapshot Snapshot, localDBOK, dockerDBHostPortOK, dockerDBRunning bool, devHostPID, devProjectPID pidStatus) []Incident {
	var incidents []Incident
	if !cfg.Exists {
		incidents = append(incidents, Incident{
			Severity:   SeverityCritical,
			Summary:    ".env ausente",
			Cause:      "O arquivo principal de configuração ainda não existe.",
			Suggestion: "Abra Config e rode env-init ou preencha o setup wizard.",
		})
	}
	if len(snapshot.Config.MissingKeys) > 0 {
		incidents = append(incidents, Incident{
			Severity:   SeverityWarning,
			Summary:    "Configuração incompleta",
			Cause:      "Há variáveis obrigatórias vazias para modos operacionais.",
			Suggestion: "Revise Config Values e preencha domínio, senhas e token quando aplicável.",
		})
	}
	if snapshot.Config.UsesLegacyFile {
		incidents = append(incidents, Incident{
			Severity:   SeverityWarning,
			Summary:    "Configuração ainda está em .env.make",
			Cause:      "A TUI leu o arquivo legado, mas docker compose usa .env como arquivo primário.",
			Suggestion: "Reabra a TUI para migrar automaticamente para .env ou salve qualquer valor na aba Config para promover o arquivo.",
		})
	}
	if !snapshot.Config.GeneratedFiles["deploy/odoo/kodoo.prod.local.conf"] {
		incidents = append(incidents, Incident{
			Severity:   SeverityWarning,
			Summary:    "Config gerada de produção ausente",
			Cause:      "O arquivo deploy/odoo/kodoo.prod.local.conf ainda não foi renderizado.",
			Suggestion: "Abra Config e rode prod-config.",
		})
	}
	if !localDBOK {
		incidents = append(incidents, Incident{
			Severity:   SeverityCritical,
			Summary:    "PostgreSQL local inacessível",
			Cause:      fmt.Sprintf("Não foi possível conectar em %s:%d.", cfg.PGLocalHost, cfg.PGLocalPort),
			Suggestion: "Abra Databases ou valide o PostgreSQL local antes de usar Dev Host.",
		})
	}
	if !dockerDBRunning {
		incidents = append(incidents, Incident{
			Severity:   SeverityWarning,
			Summary:    "Docker DB não está em execução",
			Cause:      "O container kodoo-db não está ativo, então o backend Docker não pode ser usado.",
			Suggestion: "Use Runtime para subir o stack estável ou valide o serviço db.",
		})
	} else if !dockerDBHostPortOK && snapshot.Runtime.Mode == "Dev Project" {
		incidents = append(incidents, Incident{
			Severity:   SeverityWarning,
			Summary:    "Docker DB sem bind no host",
			Cause:      fmt.Sprintf("O container db está ativo, mas a porta %s:%d não aceitou conexão.", cfg.DockerDBBindHost, cfg.DockerDBHostPort),
			Suggestion: "Reabra o modo Dev Project ou valide o override deploy/dev-project/docker-compose.db-only.yml.",
		})
	}
	if devHostPID.Exists && !devHostPID.Running {
		incidents = append(incidents, Incident{
			Severity:   SeverityWarning,
			Summary:    "PID stale em dev-host",
			Cause:      "Existe arquivo de PID do Odoo local, mas o processo não está vivo.",
			Suggestion: "Pare o modo local, limpe o PID ou reinicie via Runtime.",
		})
	}
	if devProjectPID.Exists && !devProjectPID.Running {
		incidents = append(incidents, Incident{
			Severity:   SeverityWarning,
			Summary:    "PID stale em dev-project",
			Cause:      "Existe arquivo de PID do Odoo dev-project, mas o processo não está vivo.",
			Suggestion: "Pare o modo local e suba novamente via Runtime.",
		})
	}
	if strings.TrimSpace(cfg.CloudflaredToken) == "" {
		incidents = append(incidents, Incident{
			Severity:   SeverityInfo,
			Summary:    "Tunnel sem token",
			Cause:      "CLOUDFLARED_TOKEN está vazio.",
			Suggestion: "Preencha o token antes de usar Stable Tunnel.",
		})
	}
	if cfg.ProdListDB && !tenantSafeDBFilter(cfg.ProdDBFilter) {
		incidents = append(incidents, Incident{
			Severity:   SeverityWarning,
			Summary:    "DB manager exposto com filtro amplo",
			Cause:      fmt.Sprintf("list_db está ativo e PROD_DBFILTER=%q não limita o tenant pelo host.", cfg.ProdDBFilter),
			Suggestion: "Use PROD_DBFILTER=^%d$ para rotear subdomínio -> banco e evitar exposição cruzada.",
		})
	}
	if cfg.LocalBindHost == "0.0.0.0" {
		incidents = append(incidents, Incident{
			Severity:   SeverityInfo,
			Summary:    "Bind LAN ativo",
			Cause:      fmt.Sprintf("O stack local/tunnel está publicado em %s:%d para a rede local.", cfg.LocalBindHost, cfg.LocalHTTPPort),
			Suggestion: "Garanta firewall/rede confiável antes de usar esse host fora da máquina local.",
		})
	}
	for _, check := range snapshot.Smoke {
		if check.OK {
			continue
		}
		incidents = append(incidents, Incident{
			Severity:   SeverityWarning,
			Summary:    fmt.Sprintf("%s falhou", check.Name),
			Cause:      fallback(check.Error, fmt.Sprintf("HTTP status %d", check.Code)),
			Suggestion: "Abra Logs para checar incidentes e logs crus, depois rode troubleshoot.",
		})
	}
	for _, line := range snapshot.Logs {
		upper := strings.ToUpper(line)
		if strings.Contains(upper, "ERROR") || strings.Contains(upper, "CRITICAL") {
			incidents = append(incidents, Incident{
				Severity:   SeverityWarning,
				Summary:    "Erro recente em compose logs",
				Cause:      trimLine(line, 110),
				Suggestion: "Abra Logs > Raw Logs para inspecionar o trecho bruto.",
			})
			break
		}
	}
	sortIncidents(incidents)
	return incidents
}

type pidStatus struct {
	Exists  bool
	Running bool
	PID     string
}

func readPIDStatus(path string) pidStatus {
	data, err := os.ReadFile(path)
	if err != nil {
		return pidStatus{}
	}
	pid := strings.TrimSpace(string(data))
	if pid == "" {
		return pidStatus{Exists: true}
	}
	_, err = os.Stat(filepath.Clean("/proc/" + pid))
	return pidStatus{Exists: true, Running: err == nil, PID: pid}
}

func detectMode(containers []docker.Container, devHostPID, devProjectPID pidStatus) (string, string, string) {
	if devProjectPID.Running {
		return "Dev Project", "local process", "docker"
	}
	if devHostPID.Running {
		return "Dev Host", "local process", "local"
	}
	if containerRunning(containers, "kodoo-cloudflared") {
		return "Stable Tunnel", "docker compose", "docker"
	}
	if containerRunning(containers, "kodoo-odoo") {
		return "Stable Docker", "docker compose", "docker"
	}
	if len(containers) > 0 {
		return "Stopped", "docker compose", "docker"
	}
	return "Stopped", "idle", ""
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

func serviceFromContainer(name string, containers []docker.Container) ServiceHealth {
	for _, container := range containers {
		if container.Name != name {
			continue
		}
		level := SeverityInfo
		status := strings.ToLower(container.Status)
		switch {
		case strings.HasPrefix(status, "up") || strings.Contains(status, "running"):
			level = SeverityInfo
		case strings.Contains(status, "restarting"):
			level = SeverityWarning
		default:
			level = SeverityCritical
		}
		return ServiceHealth{Name: name, Status: container.Status, Detail: container.Ports, Level: level}
	}
	return ServiceHealth{Name: name, Status: "not running", Detail: "", Level: SeverityWarning}
}

func serviceFromPort(name string, ok bool, status, detail string) ServiceHealth {
	if ok {
		return ServiceHealth{Name: name, Status: status, Detail: detail, Level: SeverityInfo}
	}
	return ServiceHealth{Name: name, Status: "unreachable", Detail: detail, Level: SeverityCritical}
}

func serviceFromDockerDB(mode string, running, hostPortOK bool, host string, port int) ServiceHealth {
	switch {
	case running && hostPortOK:
		return ServiceHealth{
			Name:   "db-docker",
			Status: "postgres docker",
			Detail: fmt.Sprintf("host bind reachable at %s:%d", host, port),
			Level:  SeverityInfo,
		}
	case running:
		level := SeverityInfo
		status := "container running (internal-only)"
		detail := "reachable from containers and docker exec; host bind is not required in this mode"
		if mode == "Dev Project" {
			level = SeverityWarning
			status = "container running (no host bind)"
			detail = fmt.Sprintf("docker exec/db-manager works; host bind %s:%d is closed", host, port)
		}
		return ServiceHealth{
			Name:   "db-docker",
			Status: status,
			Detail: detail,
			Level:  level,
		}
	default:
		return ServiceHealth{
			Name:   "db-docker",
			Status: "not running",
			Detail: "kodoo-db container is stopped",
			Level:  SeverityCritical,
		}
	}
}

func serviceFromPID(name string, pid pidStatus) ServiceHealth {
	switch {
	case pid.Running:
		return ServiceHealth{Name: name, Status: "running", Detail: "pid " + pid.PID, Level: SeverityInfo}
	case pid.Exists:
		return ServiceHealth{Name: name, Status: "stale pid", Detail: "pid " + pid.PID, Level: SeverityWarning}
	default:
		return ServiceHealth{Name: name, Status: "stopped", Detail: "", Level: SeverityInfo}
	}
}

func localPIDSummary(devHostPID, devProjectPID pidStatus) string {
	switch {
	case devProjectPID.Running:
		return "dev-project pid " + devProjectPID.PID
	case devHostPID.Running:
		return "dev-host pid " + devHostPID.PID
	case devProjectPID.Exists || devHostPID.Exists:
		return "stale pid detected"
	default:
		return "no local pid"
	}
}

func missingConfigKeys(cfg *envconfig.Config) []string {
	required := []string{"DOMAIN", "EMAIL", "PROD_DB_PASSWORD", "PROD_ADMIN_PASSWORD", "PG_LOCAL_PASSWORD", "DEV_HOST_ADMIN_PASSWORD"}
	var missing []string
	for _, key := range required {
		if strings.TrimSpace(cfg.Value(key)) == "" {
			missing = append(missing, key)
		}
	}
	return missing
}

func compatibleModes(backend string) []string {
	switch backend {
	case "docker":
		return []string{"Dev Project", "Stable Docker", "Stable Tunnel"}
	case "local":
		return []string{"Dev Host", "Local Diagnostic / Manager"}
	default:
		return []string{"unknown"}
	}
}

func preferredDBAction(backend string) string {
	if backend == "local" {
		return "dev-safe"
	}
	return "dev"
}

func connectivityLabel(backend, mode string, localDBOK, dockerDBHostPortOK, dockerDBRunning bool) string {
	switch backend {
	case "local":
		if localDBOK {
			return "ok"
		}
	case "docker":
		if dockerDBHostPortOK {
			return "ok"
		}
		if dockerDBRunning {
			if mode != "Dev Project" {
				return "internal-only"
			}
			return "container-only"
		}
	}
	return "unreachable"
}

func defaultNextStep(mode string) string {
	switch mode {
	case "Stopped":
		return "Abra Runtime e suba o modo que você quer operar agora."
	case "Stable Docker", "Stable Tunnel":
		return "Abra Logs se houver falha ou Databases para preparar um modo de desenvolvimento."
	case "Dev Host", "Dev Project":
		return "Abra Databases para trocar o cliente ou Logs para investigar incidentes."
	default:
		return "Use a palette com p para trocar de tela ou iniciar um modo."
	}
}

func portSummary(containers []docker.Container) string {
	var parts []string
	for _, container := range containers {
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

func portReachable(host string, port int) bool {
	conn, err := net.DialTimeout("tcp", net.JoinHostPort(host, fmt.Sprintf("%d", port)), 800*time.Millisecond)
	if err != nil {
		return false
	}
	_ = conn.Close()
	return true
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

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

func fallback(primary, secondary string) string {
	if strings.TrimSpace(primary) != "" {
		return primary
	}
	return secondary
}

func trimLine(line string, maxLen int) string {
	line = strings.TrimSpace(line)
	if len(line) <= maxLen {
		return line
	}
	return line[:maxLen-3] + "..."
}

func sortIncidents(incidents []Incident) {
	slices.SortFunc(incidents, func(a, b Incident) int {
		if severityWeight(a.Severity) == severityWeight(b.Severity) {
			return strings.Compare(a.Summary, b.Summary)
		}
		return severityWeight(a.Severity) - severityWeight(b.Severity)
	})
}

func severityWeight(severity Severity) int {
	switch severity {
	case SeverityCritical:
		return 0
	case SeverityWarning:
		return 1
	default:
		return 2
	}
}

func tenantSafeDBFilter(filter string) bool {
	filter = strings.TrimSpace(filter)
	if filter == "" {
		return false
	}
	return strings.Contains(filter, "%d")
}
