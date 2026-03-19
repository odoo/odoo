package database

import (
	"bufio"
	"context"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// Record describes one selectable Odoo/PostgreSQL database.
type Record struct {
	Name    string
	Backend string
	Owner   string
	Size    string
	Tags    string
}

// MsgListLoaded reports the result of a database list query.
type MsgListLoaded struct {
	Backend   string
	Databases []Record
	Err       error
}

// ListCmd loads databases from the repository db-manager helper.
func ListCmd(ctx context.Context, repoDir string, backend string) tea.Cmd {
	return func() tea.Msg {
		scriptPath := filepath.Join(repoDir, "scripts", "db-manager.sh")
		cmd := exec.CommandContext(ctx, scriptPath, "list-raw")
		cmd.Dir = repoDir
		cmd.Env = append(cmd.Environ(), "DB_MANAGER_BACKEND="+backend)
		output, err := cmd.Output()
		if err != nil {
			if exitErr, ok := err.(*exec.ExitError); ok {
				return MsgListLoaded{Backend: backend, Err: fmt.Errorf("%s", strings.TrimSpace(string(exitErr.Stderr)))}
			}
			return MsgListLoaded{Backend: backend, Err: err}
		}

		var rows []Record
		scanner := bufio.NewScanner(strings.NewReader(string(output)))
		for scanner.Scan() {
			line := strings.TrimSpace(scanner.Text())
			if line == "" {
				continue
			}
			parts := strings.SplitN(line, "|", 5)
			if len(parts) != 5 {
				continue
			}
			rows = append(rows, Record{
				Name:    parts[0],
				Backend: parts[1],
				Owner:   parts[2],
				Size:    parts[3],
				Tags:    parts[4],
			})
		}
		if err := scanner.Err(); err != nil {
			return MsgListLoaded{Backend: backend, Err: err}
		}
		return MsgListLoaded{Backend: backend, Databases: rows}
	}
}
