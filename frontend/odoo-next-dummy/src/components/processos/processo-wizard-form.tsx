"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

type WizardOption = {
  id: number;
  name: string;
};

type WizardSelection = {
  value: string;
  label: string;
};

type WizardTemplate = {
  id: number;
  name: string;
  docType: string;
  fase: string;
  processScope: string;
  isChecklist: boolean;
};

type WizardMetaResponse = {
  selections: {
    originType: WizardSelection[];
    processType: WizardSelection[];
    processScope: WizardSelection[];
  };
  ugOptions: WizardOption[];
  responsibleOptions: WizardOption[];
  defaults: {
    subject: string;
    origin_type: string;
    process_type: string;
    process_scope: string;
    ug_id: number | null;
    responsible_id: number | null;
  };
  recommendedTemplates: WizardTemplate[];
  record: {
    id: number | null;
    subject: string;
    origin_type: string;
    process_type: string;
    process_scope: string;
    ug_id: number | null;
    ug_name: string;
    responsible_id: number | null;
    responsible_name: string;
    prazo_resposta: string;
    retroativo: boolean;
    urgencia: boolean;
  };
};

type WizardPreviewResponse = {
  recommendedTemplates: WizardTemplate[];
};

type WizardSaveResponse = {
  ok: boolean;
  id: number;
};

type ProcessoWizardFormProps = {
  mode: "create" | "edit";
  recordId?: number;
  onSaved?: (id: number) => void;
  onCancel?: () => void;
};

type WizardFormState = {
  subject: string;
  origin_type: string;
  process_type: string;
  process_scope: string;
  ug_id: string;
  responsible_id: string;
  prazo_resposta: string;
  retroativo: boolean;
  urgencia: boolean;
};

function numberToFieldValue(value: number | null | undefined) {
  if (!value || !Number.isFinite(value) || value <= 0) {
    return "";
  }
  return String(value);
}

function fieldValueToNumber(value: string) {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
}

export function ProcessoWizardForm({ mode, recordId, onSaved, onCancel }: ProcessoWizardFormProps) {
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [meta, setMeta] = useState<WizardMetaResponse | null>(null);
  const [templates, setTemplates] = useState<WizardTemplate[]>([]);
  const [form, setForm] = useState<WizardFormState>({
    subject: "",
    origin_type: "",
    process_type: "",
    process_scope: "",
    ug_id: "",
    responsible_id: "",
    prazo_resposta: "",
    retroativo: false,
    urgencia: false
  });

  const canPreview = useMemo(() => {
    return Boolean(form.process_type && form.process_scope && fieldValueToNumber(form.ug_id));
  }, [form.process_scope, form.process_type, form.ug_id]);

  useEffect(() => {
    async function loadMeta() {
      try {
        setLoadingMeta(true);
        setError(null);
        setSuccess(null);

        const url =
          mode === "edit" && recordId ? `/api/gov/processos/wizard?recordId=${recordId}` : "/api/gov/processos/wizard";
        const response = await fetch(url, { cache: "no-store" });
        const payload = (await response.json()) as WizardMetaResponse & { error?: string };
        if (!response.ok) {
          throw new Error(payload.error ?? "Falha ao carregar wizard de processos");
        }

        setMeta(payload);
        setTemplates(payload.recommendedTemplates ?? []);
        setForm({
          subject: payload.record.subject ?? payload.defaults.subject ?? "",
          origin_type: payload.record.origin_type ?? payload.defaults.origin_type ?? "",
          process_type: payload.record.process_type ?? payload.defaults.process_type ?? "",
          process_scope: payload.record.process_scope ?? payload.defaults.process_scope ?? "",
          ug_id: numberToFieldValue(payload.record.ug_id ?? payload.defaults.ug_id),
          responsible_id: numberToFieldValue(payload.record.responsible_id ?? payload.defaults.responsible_id),
          prazo_resposta: payload.record.prazo_resposta ?? "",
          retroativo: Boolean(payload.record.retroativo),
          urgencia: Boolean(payload.record.urgencia)
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro inesperado ao carregar wizard");
      } finally {
        setLoadingMeta(false);
      }
    }

    void loadMeta();
  }, [mode, recordId]);

  useEffect(() => {
    if (!meta || !canPreview) {
      return;
    }

    let cancelled = false;

    async function loadTemplates() {
      try {
        setLoadingTemplates(true);
        const response = await fetch("/api/gov/processos/wizard", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            subject: form.subject,
            origin_type: form.origin_type,
            process_type: form.process_type,
            process_scope: form.process_scope,
            ug_id: fieldValueToNumber(form.ug_id),
            responsible_id: fieldValueToNumber(form.responsible_id)
          })
        });
        const payload = (await response.json()) as WizardPreviewResponse & { error?: string };
        if (!response.ok) {
          throw new Error(payload.error ?? "Falha ao carregar recomendacoes");
        }
        if (!cancelled) {
          setTemplates(payload.recommendedTemplates ?? []);
        }
      } catch {
        if (!cancelled) {
          setTemplates([]);
        }
      } finally {
        if (!cancelled) {
          setLoadingTemplates(false);
        }
      }
    }

    void loadTemplates();

    return () => {
      cancelled = true;
    };
  }, [
    canPreview,
    form.origin_type,
    form.process_scope,
    form.process_type,
    form.responsible_id,
    form.subject,
    form.ug_id,
    meta
  ]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mode === "edit" && (!recordId || recordId <= 0)) {
      setError("ID do processo invalido para edicao.");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const payload = {
        subject: form.subject,
        origin_type: form.origin_type,
        process_type: form.process_type,
        process_scope: form.process_scope,
        ug_id: fieldValueToNumber(form.ug_id),
        responsible_id: fieldValueToNumber(form.responsible_id),
        ...(mode === "edit"
          ? {
              prazo_resposta: form.prazo_resposta || null,
              retroativo: form.retroativo,
              urgencia: form.urgencia
            }
          : {})
      };

      const endpoint = mode === "create" ? "/api/gov/processos" : `/api/gov/processos/${recordId}`;
      const method = mode === "create" ? "POST" : "PATCH";

      const response = await fetch(endpoint, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = (await response.json()) as WizardSaveResponse & { error?: string };
      if (!response.ok) {
        throw new Error(result.error ?? "Falha ao salvar processo");
      }

      const message = mode === "create" ? "Processo criado via wizard com sucesso." : "Processo atualizado com sucesso.";
      setSuccess(message);
      onSaved?.(result.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado ao salvar");
    } finally {
      setSaving(false);
    }
  }

  if (loadingMeta) {
    return <p style={{ margin: 0 }}>Carregando wizard de processos...</p>;
  }

  if (!meta) {
    return <p style={{ margin: 0 }}>Nao foi possivel carregar os dados do wizard.</p>;
  }

  return (
    <form onSubmit={submit} className="wizard-form-grid">
      <label className="wizard-field">
        <span>Objeto / Assunto</span>
        <input
          required
          type="text"
          value={form.subject}
          onChange={(event) => setForm((prev) => ({ ...prev, subject: event.target.value }))}
          placeholder="Descreva o objeto do processo"
        />
      </label>

      <div className="wizard-row-3">
        <label className="wizard-field">
          <span>Origem</span>
          <select
            required
            value={form.origin_type}
            onChange={(event) => setForm((prev) => ({ ...prev, origin_type: event.target.value }))}
          >
            {meta.selections.originType.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="wizard-field">
          <span>Tipo de Processo</span>
          <select
            required
            value={form.process_type}
            onChange={(event) => setForm((prev) => ({ ...prev, process_type: event.target.value }))}
          >
            {meta.selections.processType.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="wizard-field">
          <span>Escopo</span>
          <select
            required
            value={form.process_scope}
            onChange={(event) => setForm((prev) => ({ ...prev, process_scope: event.target.value }))}
          >
            {meta.selections.processScope.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="wizard-row-2">
        <label className="wizard-field">
          <span>Unidade Gestora</span>
          <select required value={form.ug_id} onChange={(event) => setForm((prev) => ({ ...prev, ug_id: event.target.value }))}>
            <option value="">Selecione</option>
            {meta.ugOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        </label>

        <label className="wizard-field">
          <span>Responsavel</span>
          <select
            value={form.responsible_id}
            onChange={(event) => setForm((prev) => ({ ...prev, responsible_id: event.target.value }))}
          >
            <option value="">Automatico</option>
            {meta.responsibleOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {mode === "edit" && (
        <>
          <div className="wizard-row-3">
            <label className="wizard-field">
              <span>Prazo de resposta</span>
              <input
                type="date"
                value={form.prazo_resposta}
                onChange={(event) => setForm((prev) => ({ ...prev, prazo_resposta: event.target.value }))}
              />
            </label>
            <label className="wizard-toggle">
              <input
                type="checkbox"
                checked={form.retroativo}
                onChange={(event) => setForm((prev) => ({ ...prev, retroativo: event.target.checked }))}
              />
              <span>Retroativo</span>
            </label>
            <label className="wizard-toggle">
              <input
                type="checkbox"
                checked={form.urgencia}
                onChange={(event) => setForm((prev) => ({ ...prev, urgencia: event.target.checked }))}
              />
              <span>Urgencia</span>
            </label>
          </div>
        </>
      )}

      <div className="wizard-template-box">
        <div className="wizard-template-title">Modelos e checklists recomendados</div>
        {loadingTemplates && <p style={{ margin: "8px 0 0" }}>Atualizando recomendacoes...</p>}
        {!loadingTemplates && templates.length === 0 && (
          <p style={{ margin: "8px 0 0" }}>Nenhum modelo recomendado para a combinacao atual.</p>
        )}
        {!loadingTemplates && templates.length > 0 && (
          <div className="wizard-template-grid">
            {templates.map((template) => (
              <article key={template.id} className="wizard-template-item">
                <strong>{template.name}</strong>
                <small>{template.docType} | fase {template.fase}</small>
                <small>{template.processScope}</small>
                {template.isChecklist && <span className="status-badge status-ok">Checklist</span>}
              </article>
            ))}
          </div>
        )}
      </div>

      {error && <p className="action-feedback action-feedback-err">{error}</p>}
      {success && <p className="action-feedback action-feedback-ok">{success}</p>}

      <div className="wizard-actions">
        <button type="submit" disabled={saving}>
          {saving ? "Salvando..." : mode === "create" ? "Criar processo" : "Salvar alteracoes"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={saving}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  );
}
