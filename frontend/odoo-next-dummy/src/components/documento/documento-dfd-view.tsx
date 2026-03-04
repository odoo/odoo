"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { StatusState } from "@/components/ui/status-state";
import { Tabs } from "@/components/ui/tabs";

type Documento = {
  id: number;
  titulo: string;
  criadoEm: string;
  atualizadoEm: string;
  resumo: string;
};

type DocumentoDfdViewProps = {
  id: number;
};

export function DocumentoDfdView({ id }: DocumentoDfdViewProps) {
  const [data, setData] = useState<Documento | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const response = await fetch(`/api/documento-dfd/${id}`);
        if (!response.ok) {
          const payload = await response.json();
          throw new Error(payload.error ?? "Erro ao carregar documento");
        }
        const payload = (await response.json()) as Documento;
        setData(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro inesperado");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [id]);

  if (loading) {
    return <StatusState kind="loading" message="Carregando documento DFD..." />;
  }
  if (error) {
    return <StatusState kind="error" message={error} />;
  }
  if (!data) {
    return <StatusState kind="empty" message="Documento nao encontrado." />;
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Card title={data.titulo}>
        <div style={{ display: "grid", gap: 8, color: "var(--o-color-muted)", fontSize: 14 }}>
          <span>ID: {data.id}</span>
          <span>Criado em: {data.criadoEm}</span>
          <span>Atualizado em: {data.atualizadoEm}</span>
        </div>
      </Card>

      <Card title="Detalhes">
        <Tabs
          items={[
            {
              id: "resumo",
              label: "Resumo",
              content: <p>{data.resumo}</p>
            },
            {
              id: "historico",
              label: "Historico",
              content: <p>Historico simulado para demonstrar aba de timeline.</p>
            },
            {
              id: "anexos",
              label: "Anexos",
              content: <p>Aba fake para extensao futura com arquivos reais.</p>
            }
          ]}
        />
      </Card>
    </div>
  );
}
