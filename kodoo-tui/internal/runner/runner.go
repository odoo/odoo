package runner

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"os/exec"
	"sort"
	"strings"
	"sync"
	"sync/atomic"

	tea "github.com/charmbracelet/bubbletea"
)

// MsgRunnerStarted announces that a background command has been started.
type MsgRunnerStarted struct {
	ID string
}

// MsgOutputLine streams one stdout/stderr line from a running command.
type MsgOutputLine struct {
	ID   string
	Line string
}

// MsgDone reports command completion.
type MsgDone struct {
	ID       string
	Err      error
	ExitCode int
}

type result struct {
	line string
	done *MsgDone
}

var (
	sequence uint64
	streams  sync.Map
)

// Run starts a background process and returns a non-blocking Bubble Tea command.
func Run(ctx context.Context, dir string, args []string) tea.Cmd {
	id := fmt.Sprintf("cmd-%d", atomic.AddUint64(&sequence, 1))

	return func() tea.Msg {
		ch := make(chan result, 64)
		streams.Store(id, ch)
		go runProcess(ctx, id, ch, dir, args)
		return MsgRunnerStarted{ID: id}
	}
}

// Next waits for the next line or completion message of a running command.
func Next(id string) tea.Cmd {
	return func() tea.Msg {
		value, ok := streams.Load(id)
		if !ok {
			return MsgDone{ID: id, Err: errors.New("runner stream not found"), ExitCode: -1}
		}

		ch := value.(chan result)
		msg, ok := <-ch
		if !ok {
			streams.Delete(id)
			return MsgDone{ID: id, Err: nil, ExitCode: 0}
		}

		if msg.done != nil {
			streams.Delete(id)
			return *msg.done
		}

		return MsgOutputLine{ID: id, Line: msg.line}
	}
}

// MakeTarget builds "make VAR=VALUE target" and runs it in the background.
func MakeTarget(ctx context.Context, dir string, target string, vars map[string]string) tea.Cmd {
	args := []string{"make"}
	keys := make([]string, 0, len(vars))
	for key := range vars {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		args = append(args, fmt.Sprintf("%s=%s", key, vars[key]))
	}
	args = append(args, target)
	return Run(ctx, dir, args)
}

func runProcess(ctx context.Context, id string, ch chan<- result, dir string, args []string) {
	defer close(ch)

	if len(args) == 0 {
		ch <- result{done: &MsgDone{ID: id, Err: errors.New("missing command"), ExitCode: -1}}
		return
	}

	cmd := exec.CommandContext(ctx, args[0], args[1:]...)
	cmd.Dir = dir

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		ch <- result{done: &MsgDone{ID: id, Err: err, ExitCode: -1}}
		return
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		ch <- result{done: &MsgDone{ID: id, Err: err, ExitCode: -1}}
		return
	}

	if err := cmd.Start(); err != nil {
		ch <- result{done: &MsgDone{ID: id, Err: err, ExitCode: -1}}
		return
	}

	var wg sync.WaitGroup
	readPipe := func(reader io.Reader) {
		defer wg.Done()
		scanner := bufio.NewScanner(reader)
		for scanner.Scan() {
			line := strings.TrimRight(scanner.Text(), "\r\n")
			ch <- result{line: line}
		}
	}

	wg.Add(2)
	go readPipe(stdout)
	go readPipe(stderr)
	wg.Wait()

	err = cmd.Wait()
	exitCode := 0
	if err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = -1
		}
	}
	ch <- result{done: &MsgDone{ID: id, Err: err, ExitCode: exitCode}}
}
