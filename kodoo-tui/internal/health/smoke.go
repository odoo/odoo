package health

import (
	"bufio"
	"crypto/tls"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/kodoo/kodoo-tui/internal/envconfig"
)

// CheckResult captures one smoke-check result row.
type CheckResult struct {
	Name    string
	URL     string
	OK      bool
	Code    int
	Latency time.Duration
	Error   string
}

// CheckHTTP performs a simple HTTP GET with timeout measurement.
func CheckHTTP(rawURL string, timeout time.Duration) (code int, latency time.Duration, err error) {
	client := &http.Client{Timeout: timeout}
	request, err := http.NewRequest(http.MethodGet, rawURL, nil)
	if err != nil {
		return 0, 0, err
	}

	started := time.Now()
	response, err := client.Do(request)
	latency = time.Since(started)
	if err != nil {
		return 0, latency, err
	}
	defer response.Body.Close()

	return response.StatusCode, latency, nil
}

// CheckWebSocket validates a WebSocket handshake without sending frames.
func CheckWebSocket(rawURL string, key string, timeout time.Duration) (bool, error) {
	parsed, err := url.Parse(rawURL)
	if err != nil {
		return false, err
	}

	host := parsed.Host
	if !strings.Contains(host, ":") {
		if parsed.Scheme == "wss" {
			host += ":443"
		} else {
			host += ":80"
		}
	}

	dialer := &net.Dialer{Timeout: timeout}
	var conn net.Conn
	if parsed.Scheme == "wss" {
		conn, err = tls.DialWithDialer(dialer, "tcp", host, &tls.Config{
			ServerName: strings.Split(host, ":")[0],
		})
	} else {
		conn, err = dialer.Dial("tcp", host)
	}
	if err != nil {
		return false, err
	}
	defer conn.Close()

	if err := conn.SetDeadline(time.Now().Add(timeout)); err != nil {
		return false, err
	}

	path := parsed.RequestURI()
	if path == "" {
		path = "/"
	}
	request := fmt.Sprintf(
		"GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: %s\r\n\r\n",
		path,
		parsed.Host,
		key,
	)

	if _, err := conn.Write([]byte(request)); err != nil {
		return false, err
	}

	reader := bufio.NewReader(conn)
	statusLine, err := reader.ReadString('\n')
	if err != nil {
		return false, err
	}
	return strings.Contains(statusLine, "101"), nil
}

// SmokeAll runs the default local/public/WebSocket checks in parallel.
func SmokeAll(cfg *envconfig.Config) []CheckResult {
	checks := []CheckResult{
		{Name: "local-http", URL: cfg.LocalHTTPURL()},
		{Name: "local-websocket", URL: cfg.LocalWebSocketURL()},
	}
	if cfg.SMOKEPublic {
		checks = append(checks, CheckResult{Name: "public-http", URL: cfg.PublicHTTPURL()})
	}

	timeout := 6 * time.Second
	results := make([]CheckResult, len(checks))
	var wg sync.WaitGroup
	for idx, check := range checks {
		wg.Add(1)
		go func(i int, item CheckResult) {
			defer wg.Done()
			switch item.Name {
			case "local-websocket":
				started := time.Now()
				ok, err := CheckWebSocket(item.URL, "dGhlIHNhbXBsZSBub25jZQ==", timeout)
				results[i] = item
				results[i].Latency = time.Since(started)
				results[i].OK = ok && err == nil
				if err != nil {
					results[i].Error = err.Error()
				}
			default:
				code, latency, err := CheckHTTP(item.URL, timeout)
				results[i] = item
				results[i].Code = code
				results[i].Latency = latency
				results[i].OK = err == nil && code < http.StatusBadRequest
				if err != nil {
					results[i].Error = err.Error()
				}
			}
		}(idx, check)
	}
	wg.Wait()
	return results
}
