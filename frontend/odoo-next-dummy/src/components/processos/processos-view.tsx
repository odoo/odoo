import { GovListView } from "@/components/gov/gov-list-view";
import { getGovSuiteBySlug } from "@/lib/gov-suite";
import { StatusState } from "@/components/ui/status-state";

export function ProcessosView() {
  const suite = getGovSuiteBySlug("processos");
  if (!suite) {
    return <StatusState kind="error" message="Suite de processos nao configurada." />;
  }
  return <GovListView suiteKey={suite.key} />;
}
