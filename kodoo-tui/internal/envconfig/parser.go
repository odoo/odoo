package envconfig

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	PrimaryEnvFile = ".env"
	LegacyEnvFile  = ".env.make"
	ExampleEnvFile = ".env.example"
)

var (
	linePattern      = regexp.MustCompile(`^([A-Za-z_][A-Za-z0-9_]*)\s*(\?=|:=|=)\s*(.*)$`)
	expansionPattern = regexp.MustCompile(`\$\(([A-Za-z_][A-Za-z0-9_]*)\)`)
)

// Entry stores one resolved configuration value and its origin.
type Entry struct {
	Key    string
	Value  string
	Source string
}

// Config contains the typed view of the local env file used by the TUI.
type Config struct {
	Path   string
	Exists bool

	Domain                  string
	Email                   string
	CloudflaredToken        string
	ProdDBName              string
	ProdDBUser              string
	ProdDBPassword          string
	ProdAdminPassword       string
	DevHostHTTPPort         int
	DevHostDB               string
	DevHostTestDB           string
	DevHostAdminPassword    string
	DevProjectHTTPPort      int
	DevProjectDB            string
	DevProjectAdminPassword string
	PGLocalHost             string
	PGLocalPort             int
	PGLocalUser             string
	PGLocalPassword         string
	DockerDBBindHost        string
	DockerDBHostPort        int
	LocalBindHost           string
	LocalHTTPPort           int
	OllamaModel             string
	TUIRefreshSeconds       int
	TUILogLines             int
	SMOKEPublic             bool

	Values map[string]Entry
}

var defaultValues = map[string]string{
	"DOMAIN":                     "kodoo.online",
	"EMAIL":                      "",
	"CLOUDFLARED_TOKEN":          "",
	"PROD_DB_NAME":               "kodoo",
	"PROD_DB_USER":               "kodoo",
	"PROD_DB_PASSWORD":           "",
	"PROD_ADMIN_PASSWORD":        "",
	"DEV_HOST_HTTP_PORT":         "8070",
	"DEV_HOST_DB":                "kodoo",
	"DEV_HOST_TEST_DB":           "ktest",
	"DEV_PROJECT_HTTP_PORT":      "8071",
	"DEV_PROJECT_DB":             "ktest",
	"DEV_HOST_ADMIN_PASSWORD":    "",
	"DEV_PROJECT_ADMIN_PASSWORD": "",
	"PG_LOCAL_HOST":              "127.0.0.1",
	"PG_LOCAL_PORT":              "5432",
	"PG_LOCAL_USER":              "kodoo",
	"PG_LOCAL_PASSWORD":          "",
	"DOCKER_DB_BIND_HOST":        "127.0.0.1",
	"DOCKER_DB_HOST_PORT":        "5433",
	"LOCAL_BIND_HOST":            "127.0.0.1",
	"LOCAL_HTTP_PORT":            "8069",
	"OLLAMA_MODEL":               "qwen3.5:0.8b",
	"TUI_REFRESH_SECONDS":        "3",
	"TUI_LOG_LINES":              "20",
	"SMOKE_PUBLIC":               "1",
}

// ResolvePath returns .env when present, otherwise falls back to legacy .env.make.
func ResolvePath(repoDir string) string {
	primary := filepath.Join(repoDir, PrimaryEnvFile)
	if _, err := os.Stat(primary); err == nil {
		return primary
	}
	legacy := filepath.Join(repoDir, LegacyEnvFile)
	if _, err := os.Stat(legacy); err == nil {
		return legacy
	}
	return primary
}

// PrimaryPath returns the canonical .env path for the repository.
func PrimaryPath(repoDir string) string {
	return filepath.Join(repoDir, PrimaryEnvFile)
}

// Load parses .env-style files with simple Make syntax.
func Load(path string) (*Config, error) {
	cfg := &Config{
		Path:   path,
		Exists: false,
		Values: make(map[string]Entry, len(defaultValues)),
	}

	for key, value := range defaultValues {
		cfg.Values[key] = Entry{Key: key, Value: value, Source: "default"}
	}

	file, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			cfg.Path = filepath.Clean(path)
			cfg.applyTypedValues()
			return cfg, nil
		}
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer file.Close()

	cfg.Exists = true
	cfg.Path = filepath.Clean(path)

	scanner := bufio.NewScanner(file)
	lineNumber := 0
	for scanner.Scan() {
		lineNumber++
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		matches := linePattern.FindStringSubmatch(line)
		if len(matches) != 4 {
			continue
		}

		key := matches[1]
		operator := matches[2]
		value := resolve(expansionPattern.ReplaceAllStringFunc(matches[3], func(match string) string {
			keyName := expansionPattern.FindStringSubmatch(match)
			if len(keyName) != 2 {
				return match
			}
			if entry, ok := cfg.Values[keyName[1]]; ok {
				return entry.Value
			}
			return ""
		}))

		if operator == "?=" {
			if existing, ok := cfg.Values[key]; ok && existing.Source != "default" {
				continue
			}
		}

		cfg.Values[key] = Entry{
			Key:    key,
			Value:  value,
			Source: "env.make",
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("scan %s: %w", path, err)
	}

	for key := range cfg.Values {
		if value, ok := os.LookupEnv(key); ok {
			cfg.Values[key] = Entry{
				Key:    key,
				Value:  value,
				Source: "process-env",
			}
		}
	}

	cfg.applyTypedValues()
	return cfg, nil
}

// OrderedEntries returns the config entries in key order.
func (c *Config) OrderedEntries() []Entry {
	entries := make([]Entry, 0, len(c.Values))
	for _, entry := range c.Values {
		entries = append(entries, entry)
	}
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].Key < entries[j].Key
	})
	return entries
}

// Value returns the resolved value for a key.
func (c *Config) Value(key string) string {
	if entry, ok := c.Values[key]; ok {
		return entry.Value
	}
	return ""
}

// MaskedValue returns a UI-safe version of a value.
func (c *Config) MaskedValue(key string) string {
	value := c.Value(key)
	if value == "" {
		return value
	}

	if strings.Contains(strings.ToLower(key), "password") || strings.Contains(strings.ToLower(key), "token") {
		if len(value) <= 4 {
			return "****"
		}
		return value[:2] + strings.Repeat("*", len(value)-4) + value[len(value)-2:]
	}

	return value
}

// RefreshInterval returns the dashboard refresh cadence.
func (c *Config) RefreshInterval() time.Duration {
	return time.Duration(max(1, c.TUIRefreshSeconds)) * time.Second
}

// LocalHTTPURL returns the local HTTP endpoint used for smoke checks.
func (c *Config) LocalHTTPURL() string {
	return fmt.Sprintf("http://%s:%d", c.LocalBindHost, c.LocalHTTPPort)
}

// PublicHTTPURL returns the public HTTP endpoint used for smoke checks.
func (c *Config) PublicHTTPURL() string {
	return fmt.Sprintf("https://%s", c.Domain)
}

// LocalWebSocketURL returns the local WebSocket endpoint.
func (c *Config) LocalWebSocketURL() string {
	return fmt.Sprintf("ws://%s:%d/websocket", c.LocalBindHost, c.LocalHTTPPort)
}

// Set updates a configuration value in memory.
func (c *Config) Set(key, value string) {
	if c.Values == nil {
		c.Values = make(map[string]Entry)
	}
	c.Values[key] = Entry{
		Key:    key,
		Value:  value,
		Source: "env.make", // Mark as manually set/env.make source
	}
	c.applyTypedValues()
}

// Save persists the current configuration values back to the active env file.
// It tries to preserve existing comments and structure by replacing matching lines.
func (c *Config) Save() error {
	if c.Path == "" {
		return fmt.Errorf("no path defined for config")
	}

	if filepath.Base(c.Path) == LegacyEnvFile {
		c.Path = filepath.Join(filepath.Dir(c.Path), PrimaryEnvFile)
		if _, err := os.Stat(c.Path); err == nil {
			c.Exists = true
		} else {
			c.Exists = false
		}
	}

	var lines []string
	foundKeys := make(map[string]bool)

	// Read existing file if it exists
	if c.Exists {
		file, err := os.Open(c.Path)
		if err == nil {
			scanner := bufio.NewScanner(file)
			for scanner.Scan() {
				line := scanner.Text()
				trimmed := strings.TrimSpace(line)

				if trimmed == "" || strings.HasPrefix(trimmed, "#") {
					lines = append(lines, line)
					continue
				}

				matches := linePattern.FindStringSubmatch(trimmed)
				if len(matches) == 4 {
					key := matches[1]
					if entry, ok := c.Values[key]; ok && entry.Source == "env.make" {
						// Preserve the operator and spacing as much as possible
						operator := matches[2]
						lines = append(lines, fmt.Sprintf("%s %s %s", key, operator, entry.Value))
						foundKeys[key] = true
						continue
					}
				}
				lines = append(lines, line)
			}
			file.Close()
		}
	}

	// Append any new keys that weren't in the file
	sortedEntries := c.OrderedEntries()
	hasNew := false
	for _, entry := range sortedEntries {
		if entry.Source == "env.make" && !foundKeys[entry.Key] {
			if !hasNew && len(lines) > 0 && lines[len(lines)-1] != "" {
				lines = append(lines, "")
			}
			lines = append(lines, fmt.Sprintf("%s = %s", entry.Key, entry.Value))
			foundKeys[entry.Key] = true
			hasNew = true
		}
	}

	// Write back to file
	err := os.WriteFile(c.Path, []byte(strings.Join(lines, "\n")+"\n"), 0644)
	if err != nil {
		return fmt.Errorf("write %s: %w", c.Path, err)
	}
	c.Exists = true
	return nil
}

func (c *Config) applyTypedValues() {
	c.Domain = c.Value("DOMAIN")
	c.Email = c.Value("EMAIL")
	c.CloudflaredToken = c.Value("CLOUDFLARED_TOKEN")
	c.ProdDBName = c.Value("PROD_DB_NAME")
	c.ProdDBUser = c.Value("PROD_DB_USER")
	c.ProdDBPassword = c.Value("PROD_DB_PASSWORD")
	c.ProdAdminPassword = c.Value("PROD_ADMIN_PASSWORD")
	c.DevHostHTTPPort = atoi(c.Value("DEV_HOST_HTTP_PORT"), 8070)
	c.DevHostDB = c.Value("DEV_HOST_DB")
	c.DevHostTestDB = c.Value("DEV_HOST_TEST_DB")
	c.DevHostAdminPassword = c.Value("DEV_HOST_ADMIN_PASSWORD")
	c.DevProjectHTTPPort = atoi(c.Value("DEV_PROJECT_HTTP_PORT"), 8071)
	c.DevProjectDB = c.Value("DEV_PROJECT_DB")
	c.DevProjectAdminPassword = c.Value("DEV_PROJECT_ADMIN_PASSWORD")
	c.PGLocalHost = c.Value("PG_LOCAL_HOST")
	c.PGLocalPort = atoi(c.Value("PG_LOCAL_PORT"), 5432)
	c.PGLocalUser = c.Value("PG_LOCAL_USER")
	c.PGLocalPassword = c.Value("PG_LOCAL_PASSWORD")
	c.DockerDBBindHost = c.Value("DOCKER_DB_BIND_HOST")
	c.DockerDBHostPort = atoi(c.Value("DOCKER_DB_HOST_PORT"), 5433)
	c.LocalBindHost = c.Value("LOCAL_BIND_HOST")
	c.LocalHTTPPort = atoi(c.Value("LOCAL_HTTP_PORT"), 8069)
	c.OllamaModel = c.Value("OLLAMA_MODEL")
	c.TUIRefreshSeconds = atoi(c.Value("TUI_REFRESH_SECONDS"), 3)
	c.TUILogLines = atoi(c.Value("TUI_LOG_LINES"), 20)
	c.SMOKEPublic = toBool(c.Value("SMOKE_PUBLIC"))
}

func resolve(value string) string {
	value = strings.TrimSpace(value)
	if len(value) >= 2 {
		if (strings.HasPrefix(value, "\"") && strings.HasSuffix(value, "\"")) || (strings.HasPrefix(value, "'") && strings.HasSuffix(value, "'")) {
			return value[1 : len(value)-1]
		}
	}
	return value
}

func atoi(raw string, fallback int) int {
	value, err := strconv.Atoi(strings.TrimSpace(raw))
	if err != nil {
		return fallback
	}
	return value
}

func toBool(raw string) bool {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "1", "true", "yes", "on":
		return true
	default:
		return false
	}
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
