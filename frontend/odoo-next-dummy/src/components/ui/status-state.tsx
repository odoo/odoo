type StatusStateProps = {
  kind: "loading" | "error" | "empty";
  message: string;
};

const colors = {
  loading: "var(--o-color-muted)",
  error: "var(--o-color-danger)",
  empty: "var(--o-color-muted)"
};

export function StatusState({ kind, message }: StatusStateProps) {
  return (
    <div
      role={kind === "error" ? "alert" : "status"}
      style={{
        border: "1px dashed var(--o-color-border)",
        borderRadius: "var(--o-radius)",
        padding: 20,
        color: colors[kind],
        background: "linear-gradient(180deg, #fffdf9, #f8f3e8)"
      }}
    >
      {message}
    </div>
  );
}
