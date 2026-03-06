"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ProcessoWizardForm } from "@/components/processos/processo-wizard-form";
import { Card } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { StatusState } from "@/components/ui/status-state";
import { GovSuiteConfig, GovSuiteKey, govSuiteConfig } from "@/lib/gov-suite";

type GovItem = {
  id: number;
  nome: string;
  estado: string;
  destaqueLabel: string;
  destaque: string;
  criadoEm: string;
  atualizadoEm: string;
};

type GovListResponse = {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  items: GovItem[];
};

type GovListViewProps = {
  suiteKey: GovSuiteKey;
};

function getStatusTone(value: string) {
  const normalized = (value || "").toLowerCase();
  if (
    normalized.includes("cancel") ||
    normalized.includes("rejeit") ||
    normalized.includes("erro") ||
    normalized.includes("bloq")
  ) {
    return "status-crit";
  }
  if (
    normalized.includes("rascunho") ||
    normalized.includes("revis") ||
    normalized.includes("pend") ||
    normalized.includes("aguard")
  ) {
    return "status-warn";
  }
  return "status-ok";
}

function getListColumns(suite: GovSuiteConfig, highlightLabel: string) {
  const base = [
    { key: "id" as const, label: "ID" },
    {
      key: "nome" as const,
      label: "Nome",
      render: (row: GovItem) => (
        <Link href={suite.detailPath(row.id)} style={{ color: "var(--o-color-primary-700)", fontWeight: 700 }}>
          {row.nome}
        </Link>
      )
    },
    { key: "destaque" as const, label: highlightLabel }
  ];

  if (suite.key === "dotacoes" || suite.key === "execucoes") {
    return [
      ...base,
      { key: "criadoEm" as const, label: "Criado em" },
      {
        key: "estado" as const,
        label: "Estado",
        render: (row: GovItem) => <span className={`status-badge ${getStatusTone(row.estado)}`}>{row.estado}</span>
      }
    ];
  }
  if (suite.key === "ai_templates" || suite.key === "ai_memory") {
    return [
      ...base,
      {
        key: "estado" as const,
        label: "Estado",
        render: (row: GovItem) => <span className={`status-badge ${getStatusTone(row.estado)}`}>{row.estado}</span>
      },
      { key: "atualizadoEm" as const, label: "Atualizado em" }
    ];
  }
  return [
    ...base,
    {
      key: "estado" as const,
      label: "Estado",
      render: (row: GovItem) => <span className={`status-badge ${getStatusTone(row.estado)}`}>{row.estado}</span>
    },
    { key: "atualizadoEm" as const, label: "Atualizado em" }
  ];
}

export function GovListView({ suiteKey }: GovListViewProps) {
  const suite = govSuiteConfig[suiteKey] as GovSuiteConfig;

  const [page, setPage] = useState(1);
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [appliedFilters, setAppliedFilters] = useState<Record<string, string>>({});
  const [data, setData] = useState<GovListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);
  const [showCreateWizard, setShowCreateWizard] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const params = new URLSearchParams({
          page: String(page),
          pageSize: "10"
        });
        for (const [key, value] of Object.entries(appliedFilters)) {
          if (value) {
            params.set(key, value);
          }
        }

        const response = await fetch(`/api/gov/${suite.key.replaceAll("_", "-")}?${params.toString()}`);
        if (!response.ok) {
          const payload = await response.json();
          throw new Error(payload.error ?? "Erro ao carregar dados da suite gov");
        }
        const payload = (await response.json()) as GovListResponse;
        setData(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro inesperado");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [page, suite.key, appliedFilters, refreshTick]);

  function applyFilters() {
    setPage(1);
    setAppliedFilters(
      Object.fromEntries(Object.entries(filterValues).filter(([, value]) => value && value.trim() !== ""))
    );
  }

  function clearFilters() {
    setFilterValues({});
    setAppliedFilters({});
    setPage(1);
  }

  function handleProcessCreated() {
    setShowCreateWizard(false);
    setPage(1);
    setRefreshTick((current) => current + 1);
  }

  if (loading) {
    return <StatusState kind="loading" message={`Carregando ${suite.label.toLowerCase()}...`} />;
  }
  if (error) {
    return <StatusState kind="error" message={error} />;
  }
  if (!data) {
    return <StatusState kind="empty" message={`Nenhum registro em ${suite.label}.`} />;
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <section className="suite-hero">
        <h2>{suite.label}</h2>
        <p>Consulta operacional da suite com filtros dinâmicos e acesso rápido ao detalhe.</p>
      </section>

      <section className="kpi-grid">
        <div className="kpi-tile">
          <small>Total</small>
          <strong>{data.total}</strong>
        </div>
        <div className="kpi-tile">
          <small>Página</small>
          <strong>{data.page}</strong>
        </div>
        <div className="kpi-tile">
          <small>Total de páginas</small>
          <strong>{data.totalPages}</strong>
        </div>
      </section>

      {suite.key === "processos" && (
        <Card title="Wizard de Processo">
          <div className="wizard-header-actions">
            <button type="button" onClick={() => setShowCreateWizard((current) => !current)}>
              {showCreateWizard ? "Ocultar criacao" : "Novo processo"}
            </button>
          </div>
          {showCreateWizard && (
            <ProcessoWizardForm mode="create" onSaved={handleProcessCreated} onCancel={() => setShowCreateWizard(false)} />
          )}
        </Card>
      )}

      {(suite.filters?.length ?? 0) > 0 && (
        <Card title="Filtros">
          <div className="filter-grid">
            {suite.filters?.map((filter) => {
              if (filter.kind === "select") {
                return (
                  <label key={filter.param} className="filter-field">
                    <span>{filter.label}</span>
                    <select
                      value={filterValues[filter.param] ?? ""}
                      onChange={(event) =>
                        setFilterValues((prev) => ({ ...prev, [filter.param]: event.target.value }))
                      }
                      style={{ padding: "8px 10px" }}
                    >
                      {(filter.options ?? []).map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                );
              }

              return (
                <label key={filter.param} className="filter-field">
                  <span>{filter.label}</span>
                  <input
                    type={filter.kind === "number" ? "number" : "text"}
                    value={filterValues[filter.param] ?? ""}
                    onChange={(event) => setFilterValues((prev) => ({ ...prev, [filter.param]: event.target.value }))}
                    style={{ padding: "8px 10px" }}
                  />
                </label>
              );
            })}
          </div>
          <div className="filter-actions">
            <button type="button" onClick={applyFilters} style={{ padding: "8px 12px" }}>
              Aplicar filtros
            </button>
            <button type="button" onClick={clearFilters} style={{ padding: "8px 12px" }}>
              Limpar
            </button>
          </div>
        </Card>
      )}

      <Card title={`${suite.label} (${data.total})`}>
        {data.items.length === 0 ? (
          <StatusState kind="empty" message={`Nenhum registro em ${suite.label}.`} />
        ) : (
          <DataTable
            rows={data.items}
            columns={getListColumns(suite, data.items[0]?.destaqueLabel ?? "Destaque")}
          />
        )}
      </Card>
      <div className="pagination-bar">
        <button
          type="button"
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          style={{ padding: "8px 12px" }}
        >
          Anterior
        </button>
        <span style={{ color: "var(--o-color-muted)" }}>
          Pagina {data.page} de {data.totalPages}
        </span>
        <button
          type="button"
          onClick={() => setPage((p) => Math.min(data.totalPages, p + 1))}
          disabled={page >= data.totalPages}
          style={{ padding: "8px 12px" }}
        >
          Proxima
        </button>
      </div>
    </div>
  );
}
