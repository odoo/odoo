package health

import (
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/kodoo/kodoo-tui/internal/envconfig"
)

// CheckResult captures one smoke-check result row.
type CheckResult struct {
	Name    string
	URL     string
	Host    string
	OK      bool
	Code    int
	Latency time.Duration
	Error   string
}

// CheckHTTP performs a simple HTTP GET with timeout measurement.
func CheckHTTP(rawURL string, timeout time.Duration, host string) (code int, latency time.Duration, err error) {
	client := &http.Client{Timeout: timeout}
	request, err := http.NewRequest(http.MethodGet, rawURL, nil)
	if err != nil {
		return 0, 0, err
	}
	if strings.TrimSpace(host) != "" {
		request.Host = host
		request.Header.Set("Host", host)
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

// SmokeAll runs the default local/public/WebSocket checks in parallel.
func SmokeAll(cfg *envconfig.Config) []CheckResult {
	checks := []CheckResult{
		{Name: "local-http", URL: cfg.LocalHTTPURL()},
		{Name: "local-websocket", URL: cfg.LocalHTTPURL() + "/websocket/health", Host: cfg.Domain},
	}
	if cfg.SMOKEPublic {
		checks = append(checks,
			CheckResult{Name: "public-http", URL: cfg.PublicHTTPURL()},
			CheckResult{Name: "public-www", URL: cfg.PublicWWWURL()},
		)
	}

	timeout := 6 * time.Second
	results := make([]CheckResult, len(checks))
	var wg sync.WaitGroup
	for idx, check := range checks {
		wg.Add(1)
		go func(i int, item CheckResult) {
			defer wg.Done()
			code, latency, err := CheckHTTP(item.URL, timeout, item.Host)
			results[i] = item
			results[i].Code = code
			results[i].Latency = latency
			results[i].OK = err == nil && code < http.StatusBadRequest
			if err != nil {
				results[i].Error = err.Error()
			}
		}(idx, check)
	}
	wg.Wait()
	return results
}
