"use client";

import { useEffect, useState } from "react";
import { ProcessoWizardForm } from "@/components/processos/processo-wizard-form";
import { Card } from "@/components/ui/card";
import { StatusState } from "@/components/ui/status-state";
import { Tabs } from "@/components/ui/tabs";
import { GovSuiteConfig, GovSuiteKey, govSuiteConfig } from "@/lib/gov-suite";

type GovRecord = {
  id: number;
  nome: string;
  estado: string;
  destaqueLabel: string;
  destaque: string;
  criadoEm: string;
  atualizadoEm: string;
  resumo: string;
  actions?: Array<{
    funcao: string;
    label: string;
    tone: "primary" | "warn" | "danger" | "neutral";
  }>;
  detalhes: Array<{ label: string; value: string }>;
};

type GovDetailViewProps = {
  suiteKey: GovSuiteKey;
  id: number;
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

export function GovDetailView({ suiteKey, id }: GovDetailViewProps) {
  const suite = govSuiteConfig[suiteKey] as GovSuiteConfig;
  const [data, setData] = useState<GovRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showEditWizard, setShowEditWizard] = useState(false);
  const [reloadTick, setReloadTick] = useState(0);

  async function runAction(funcao: string) {
    try {
      setRunningAction(funcao);
      setActionError(null);
      setActionFeedback(null);
      const response = await fetch(`/api/gov/${suite.key.replaceAll("_", "-")}/${id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ funcao })
      });
      const payload = (await response.json()) as { error?: string; record?: GovRecord };
      if (!response.ok) {
        throw new Error(payload.error ?? "Falha ao executar acao");
      }
      if (payload.record) {
        setData(payload.record);
      }
      setActionFeedback(`Funcao ${funcao} executada com sucesso.`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Erro inesperado ao executar acao.");
    } finally {
      setRunningAction(null);
    }
  }

  function getActionStyle(tone: "primary" | "warn" | "danger" | "neutral") {
    if (tone === "primary") {
      return {
        background: "linear-gradient(90deg, var(--o-color-primary), var(--o-color-primary-700))",
        color: "white",
        borderColor: "rgba(28, 130, 120, 0.9)"
      };
    }
    if (tone === "warn") {
      return {
        background: "linear-gradient(90deg, #f59e0b, #d97706)",
        color: "white",
        borderColor: "rgba(180, 110, 8, 0.9)"
      };
    }
    if (tone === "danger") {
      return {
        background: "linear-gradient(90deg, #dc2626, #b91c1c)",
        color: "white",
        borderColor: "rgba(161, 20, 20, 0.9)"
      };
    }
    return {
      background: "linear-gradient(180deg, #fffefb, #f7f2e8)",
      color: "var(--o-color-text)",
      borderColor: "var(--o-color-border)"
    };
  }

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
  }, [id, suite.key, reloadTick]);

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
      <section className="suite-hero">
        <h2>{suite.label} - Detalhe</h2>
        <p>Leitura operacional do registro com metadados consolidados.</p>
      </section>

      <Card title={`${suite.label} #${data.id}`}>
        <div className="kv-grid">
          <div className="kv-item">
            <small>Nome</small>
            <strong>{data.nome}</strong>
          </div>
          <div className="kv-item">
            <small>{data.destaqueLabel}</small>
            <strong>{data.destaque}</strong>
          </div>
          <div className="kv-item">
            <small>Estado</small>
            <span className={`status-badge ${getStatusTone(data.estado)}`}>{data.estado}</span>
          </div>
          <div className="kv-item">
            <small>Criado em</small>
            <strong>{data.criadoEm}</strong>
          </div>
          <div className="kv-item">
            <small>Atualizado em</small>
            <strong>{data.atualizadoEm}</strong>
          </div>
        </div>
      </Card>

      {suite.key === "processos" && (
        <Card title="Editar Processo (Wizard)">
          <div className="wizard-header-actions">
            <button type="button" onClick={() => setShowEditWizard((current) => !current)}>
              {showEditWizard ? "Fechar edicao" : "Editar dados do processo"}
            </button>
          </div>
          {showEditWizard && (
            <ProcessoWizardForm
              mode="edit"
              recordId={id}
              onSaved={() => {
                setShowEditWizard(false);
                setReloadTick((current) => current + 1);
              }}
              onCancel={() => setShowEditWizard(false)}
            />
          )}
        </Card>
      )}

      {(data.actions?.length ?? 0) > 0 && (
        <Card title="Acoes operacionais">
          <div className="action-grid">
            {data.actions?.map((action) => (
              <button
                key={action.funcao}
                type="button"
                onClick={() => void runAction(action.funcao)}
                disabled={runningAction !== null}
                style={{
                  padding: "10px 12px",
                  fontWeight: 700,
                  ...(getActionStyle(action.tone) as object)
                }}
              >
                {runningAction === action.funcao ? "Executando..." : action.label}
              </button>
            ))}
          </div>
          {actionFeedback && <p className="action-feedback action-feedback-ok">{actionFeedback}</p>}
          {actionError && <p className="action-feedback action-feedback-err">{actionError}</p>}
        </Card>
      )}

      <Card title="Visao detalhada">
        <Tabs
          items={[
            {
              id: "resumo",
              label: "Resumo",
              content: (
                <div className="kv-item">
                  <small>Contexto</small>
                  <p style={{ margin: 0 }}>{data.resumo}</p>
                </div>
              )
            },
            {
              id: "metadados",
              label: "Metadados",
              content: (
                <div className="kv-grid">
                  {data.detalhes.length === 0 && <p>Nenhum metadado adicional disponivel.</p>}
                  {data.detalhes.map((item) => (
                    <div key={item.label} className="kv-item">
                      <small>{item.label}</small>
                      <strong>{item.value}</strong>
                    </div>
                  ))}
                </div>
              )
            },
            {
              id: "anexos",
              label: "Anexos",
              content: (
                <div className="kv-item">
                  <small>Arquivos</small>
                  <p style={{ margin: 0 }}>Area placeholder para anexos futuros.</p>
                </div>
              )
            }
          ]}
        />
      </Card>
    </div>
  );
}
