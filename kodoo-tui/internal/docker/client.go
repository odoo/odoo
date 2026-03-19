package docker

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
	"sync"
)

// Container describes one Docker container visible to the current engine.
type Container struct {
	Name   string
	Image  string
	Status string
	Ports  string
}

// Stat contains one docker stats snapshot.
type Stat struct {
	Name       string
	CPUPercent float64
	MemPercent float64
	MemUsage   string
}

type dockerPSRow struct {
	Names   string `json:"Names"`
	Image   string `json:"Image"`
	Status  string `json:"Status"`
	Ports   string `json:"Ports"`
	Name    string `json:"Name"`
	CPUPerc string `json:"CPUPerc"`
	MemPerc string `json:"MemPerc"`
	MemUsage string `json:"MemUsage"`
}

// ListContainers uses the Docker CLI for compatibility with local setups.
func ListContainers() ([]Container, error) {
	cmd := exec.Command("docker", "ps", "-a", "--format", "json")
	output, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	var containers []Container
	scanner := bufio.NewScanner(bytes.NewReader(output))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}

		var row dockerPSRow
		if err := json.Unmarshal([]byte(line), &row); err != nil {
			return nil, fmt.Errorf("parse docker ps row: %w", err)
		}

		name := row.Names
		if name == "" {
			name = row.Name
		}
		containers = append(containers, Container{
			Name:   name,
			Image:  row.Image,
			Status: row.Status,
			Ports:  row.Ports,
		})
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return containers, nil
}

// Stats returns one non-streaming docker stats snapshot.
func Stats() ([]Stat, error) {
	cmd := exec.Command("docker", "stats", "--no-stream", "--format", "json")
	output, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	var stats []Stat
	scanner := bufio.NewScanner(bytes.NewReader(output))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}

		var row dockerPSRow
		if err := json.Unmarshal([]byte(line), &row); err != nil {
			return nil, fmt.Errorf("parse docker stats row: %w", err)
		}

		stats = append(stats, Stat{
			Name:       row.Name,
			CPUPercent: parsePercent(row.CPUPerc),
			MemPercent: parsePercent(row.MemPerc),
			MemUsage:   row.MemUsage,
		})
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return stats, nil
}

// StreamLogs follows docker compose logs and sends plain lines to ch.
func StreamLogs(ctx context.Context, service string, lines int, ch chan<- string) {
	defer close(ch)

	args := []string{"compose", "logs", "--follow", fmt.Sprintf("--tail=%d", max(lines, 1))}
	if service != "" && service != "todos" {
		args = append(args, service)
	}

	cmd := exec.CommandContext(ctx, "docker", args...)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		ch <- fmt.Sprintf("error: %v", err)
		return
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		ch <- fmt.Sprintf("error: %v", err)
		return
	}

	if err := cmd.Start(); err != nil {
		ch <- fmt.Sprintf("error: %v", err)
		return
	}

	var wg sync.WaitGroup
	readPipe := func(scanner *bufio.Scanner) {
		defer wg.Done()
		for scanner.Scan() {
			ch <- scanner.Text()
		}
	}

	wg.Add(2)
	go readPipe(bufio.NewScanner(stdout))
	go readPipe(bufio.NewScanner(stderr))
	wg.Wait()
	_ = cmd.Wait()
}

// TailLogs reads a recent docker compose log snapshot.
func TailLogs(lines int, service string) ([]string, error) {
	args := []string{"compose", "logs", fmt.Sprintf("--tail=%d", max(lines, 1))}
	if service != "" && service != "todos" {
		args = append(args, service)
	}
	cmd := exec.Command("docker", args...)
	output, err := cmd.CombinedOutput()
	if err != nil && len(output) == 0 {
		return nil, err
	}

	result := make([]string, 0, lines)
	scanner := bufio.NewScanner(bytes.NewReader(output))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		result = append(result, line)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}

	if len(result) > lines {
		result = result[len(result)-lines:]
	}
	return result, nil
}

// Services returns the running compose service names for the current project.
func Services() ([]string, error) {
	cmd := exec.Command("docker", "compose", "ps", "--services")
	output, err := cmd.Output()
	if err != nil {
		return nil, err
	}
	scanner := bufio.NewScanner(bytes.NewReader(output))
	services := []string{"todos"}
	for scanner.Scan() {
		service := strings.TrimSpace(scanner.Text())
		if service == "" {
			continue
		}
		services = append(services, service)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return services, nil
}

func parsePercent(raw string) float64 {
	raw = strings.TrimSuffix(strings.TrimSpace(raw), "%")
	value, err := strconv.ParseFloat(raw, 64)
	if err != nil {
		return 0
	}
	return value
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
