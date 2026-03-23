package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/kodoo/kodoo-tui/internal/app"
	"github.com/kodoo/kodoo-tui/internal/envconfig"
)

type bootstrapPrompt struct {
	Key         string
	Label       string
	DefaultFrom string
	Required    bool
}

func main() {
	cwd, err := os.Getwd()
	if err != nil {
		fmt.Fprintf(os.Stderr, "resolve cwd: %v\n", err)
		os.Exit(1)
	}

	configPath := envconfig.PrimaryPath(cwd)
	if err := ensureEnvFile(cwd, configPath, os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "prepare env file: %v\n", err)
		os.Exit(1)
	}

	cfg, err := envconfig.Load(configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "load %s: %v\n", filepath.Base(configPath), err)
		os.Exit(1)
	}

	program := tea.NewProgram(
		app.New(cfg, cwd),
		tea.WithAltScreen(),
	)
	if _, err := program.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "kodoo-tui: %v\n", err)
		os.Exit(1)
	}
}

func ensureEnvFile(repoDir, configPath string, in io.Reader, out io.Writer) error {
	if _, err := os.Stat(configPath); err == nil {
		return nil
	}

	legacyPath := filepath.Join(repoDir, envconfig.LegacyEnvFile)
	if configPath != legacyPath {
		if _, err := os.Stat(legacyPath); err == nil {
			fmt.Fprintf(out, "Nenhum .env encontrado. Vou migrar o legado %s para %s.\n", envconfig.LegacyEnvFile, envconfig.PrimaryEnvFile)
			data, readErr := os.ReadFile(legacyPath)
			if readErr != nil {
				return readErr
			}
			return os.WriteFile(configPath, data, 0o600)
		}
	}

	examplePath := filepath.Join(repoDir, envconfig.ExampleEnvFile)
	if _, err := os.Stat(examplePath); err != nil {
		return fmt.Errorf("missing %s", envconfig.ExampleEnvFile)
	}

	reader := bufio.NewReader(in)
	fmt.Fprintf(out, "\nKODOO TUI · configuração inicial\n")
	fmt.Fprintf(out, "Não encontrei %s. Vou criar um agora com algumas perguntas rápidas.\n\n", envconfig.PrimaryEnvFile)

	templateData, err := os.ReadFile(examplePath)
	if err != nil {
		return err
	}
	if err := os.WriteFile(configPath, templateData, 0o600); err != nil {
		return err
	}

	cfg, err := envconfig.Load(configPath)
	if err != nil {
		return err
	}

	prompts := []bootstrapPrompt{
		{Key: "DOMAIN", Label: "Domínio público do sistema", DefaultFrom: cfg.Domain, Required: true},
		{Key: "EMAIL", Label: "Email administrativo/Let's Encrypt", DefaultFrom: cfg.Email, Required: true},
		{Key: "PROD_DB_PASSWORD", Label: "Senha do banco de produção", DefaultFrom: cfg.ProdDBPassword, Required: true},
		{Key: "PROD_ADMIN_PASSWORD", Label: "Senha admin do Odoo em produção", DefaultFrom: cfg.ProdAdminPassword, Required: true},
		{Key: "PG_LOCAL_PASSWORD", Label: "Senha do PostgreSQL local", DefaultFrom: cfg.PGLocalPassword, Required: true},
		{Key: "DEV_HOST_ADMIN_PASSWORD", Label: "Senha admin do Odoo local (dev-host)", DefaultFrom: cfg.DevHostAdminPassword, Required: true},
		{Key: "CLOUDFLARED_TOKEN", Label: "Token do Cloudflared (opcional)", DefaultFrom: cfg.CloudflaredToken, Required: false},
	}

	for _, prompt := range prompts {
		value, err := askValue(reader, out, prompt)
		if err != nil {
			return err
		}
		cfg.Set(prompt.Key, value)
	}

	if cfg.Value("DEV_PROJECT_ADMIN_PASSWORD") == "" {
		cfg.Set("DEV_PROJECT_ADMIN_PASSWORD", cfg.Value("DEV_HOST_ADMIN_PASSWORD"))
	}
	if cfg.Value("PG_LOCAL_PASSWORD") != "" && cfg.Value("PROD_DB_PASSWORD") == "" {
		cfg.Set("PROD_DB_PASSWORD", cfg.Value("PG_LOCAL_PASSWORD"))
	}

	if err := cfg.Save(); err != nil {
		return err
	}

	fmt.Fprintf(out, "\nArquivo %s criado com sucesso. Você pode ajustar o resto depois na aba Config do TUI.\n\n", envconfig.PrimaryEnvFile)
	return nil
}

func askValue(reader *bufio.Reader, out io.Writer, prompt bootstrapPrompt) (string, error) {
	for {
		label := prompt.Label
		if prompt.Required {
			label += " [obrigatório]"
		} else {
			label += " [opcional]"
		}
		if prompt.DefaultFrom != "" {
			fmt.Fprintf(out, "%s [%s]: ", label, prompt.DefaultFrom)
		} else {
			fmt.Fprintf(out, "%s: ", label)
		}

		raw, err := reader.ReadString('\n')
		if err != nil && err != io.EOF {
			return "", err
		}
		value := strings.TrimSpace(raw)
		if value == "" {
			value = prompt.DefaultFrom
		}
		if value == "" && prompt.Required {
			fmt.Fprintln(out, "Esse campo é obrigatório. Tente de novo.")
			if err == io.EOF {
				return "", io.ErrUnexpectedEOF
			}
			continue
		}
		return value, nil
	}
}
