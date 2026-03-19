package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/kodoo/kodoo-tui/internal/app"
	"github.com/kodoo/kodoo-tui/internal/envconfig"
)

func main() {
	cwd, err := os.Getwd()
	if err != nil {
		fmt.Fprintf(os.Stderr, "resolve cwd: %v\n", err)
		os.Exit(1)
	}

	cfg, err := envconfig.Load(".env.make")
	if err != nil {
		fmt.Fprintf(os.Stderr, "load .env.make: %v\n", err)
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
