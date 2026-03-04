"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { StatusState } from "@/components/ui/status-state";
import { Tabs } from "@/components/ui/tabs";
import { GovSuiteConfig } from "@/lib/gov-suite";

type GovRecord = {
  id: number;
  nome: string;
  estado: string;
  criadoEm: string;
  atualizadoEm: string;
  resumo: string;
};

type GovDetailViewProps = {
  suite: GovSuiteConfig;
  id: number;
};

export function GovDetailView({ suite, id }: GovDetailViewProps) {
  const [data, setData] = useState<GovRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const response = await fetch(`/api/gov/${suite.key.replaceAll("_", "-")}/${id}`);
        if (!response.ok) {
          const payload = await response.json();
          throw new Error(payload.error ?? "Erro ao carregar detalhe");
        }
        const payload = (await response.json()) as GovRecord;
        setData(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro inesperado");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [id, suite.key]);

  if (loading) {
    return <StatusState kind="loading" message={`Carregando detalhe de ${suite.label.toLowerCase()}...`} />;
  }
  if (error) {
    return <StatusState kind="error" message={error} />;
  }
  if (!data) {
    return <StatusState kind="empty" message="Registro nao encontrado." />;
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Card title={`${suite.label} #${data.id}`}>
        <div style={{ display: "grid", gap: 8, color: "var(--o-color-muted)", fontSize: 14 }}>
          <span>Nome: {data.nome}</span>
          <span>Estado: {data.estado}</span>
          <span>Criado em: {data.criadoEm}</span>
          <span>Atualizado em: {data.atualizadoEm}</span>
        </div>
      </Card>

      <Card title="Abas">
        <Tabs
          items={[
            { id: "resumo", label: "Resumo", content: <p>{data.resumo}</p> },
            { id: "workflow", label: "Workflow", content: <p>Workflow fake para validar UX da suite.</p> },
            { id: "anexos", label: "Anexos", content: <p>Area placeholder para anexos futuros.</p> }
          ]}
        />
      </Card>
    </div>
  );
}
