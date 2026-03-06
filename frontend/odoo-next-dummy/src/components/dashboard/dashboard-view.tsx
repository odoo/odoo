"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { StatusState } from "@/components/ui/status-state";
import { govSuiteList } from "@/lib/gov-suite";

type DashboardData = {
  totalProcessos: number;
  latest: Array<{ id: number; nome: string; atualizadoEm: string }>;
  byState: Array<{ state: string; total: number }>;
};

export function DashboardView() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function run() {
      try {
        setLoading(true);
        const response = await fetch("/api/dashboard");
        if (!response.ok) {
          const payload = await response.json();
          throw new Error(payload.error ?? "Erro no dashboard");
        }
        const payload = (await response.json()) as DashboardData;
        setData(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro inesperado");
      } finally {
        setLoading(false);
      }
    }
    void run();
  }, []);

  if (loading) {
    return <StatusState kind="loading" message="Carregando dashboard..." />;
  }
  if (error) {
    return <StatusState kind="error" message={error} />;
  }
  if (!data || data.latest.length === 0) {
    return <StatusState kind="empty" message="Nenhum dado encontrado no Odoo para o dashboard." />;
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <section className="dash-hero">
        <strong style={{ fontSize: 20 }}>Centro de Comando Governamental</strong>
        <small>
          Visao consolidada da trilha ETP -&gt; DFD -&gt; Compras -&gt; NE -&gt; NL -&gt; OP com acesso rapido por modulo.
        </small>
      </section>

      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        <Card title="Total de Processos" value={data.totalProcessos} />
        <Card title="Estados mapeados" value={data.byState.length} />
        <Card title="Ultima sincronizacao" value={new Date().toLocaleTimeString("pt-BR")} />
      </div>
      <Card title="Ultimos processos">
        <DataTable
          rows={data.latest}
          columns={[
            { key: "id", label: "ID" },
            { key: "nome", label: "Nome" },
            { key: "atualizadoEm", label: "Atualizado em" }
          ]}
        />
      </Card>
      <Card title="Acesso rapido Gov Suite">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10 }}>
          {govSuiteList.map((suite) => (
            <Link
              key={suite.key}
              href={suite.path}
              style={{
                border: "1px solid var(--o-color-border)",
                borderRadius: 8,
                padding: "10px 12px",
                color: "var(--o-color-primary-700)",
                fontWeight: 700,
                background: "linear-gradient(180deg, #fffefb, #f8f2e4)"
              }}
            >
              {suite.label}
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}
