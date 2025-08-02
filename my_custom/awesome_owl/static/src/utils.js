import { useRef, onMounted } from "@odoo/owl";

export function useAutoFocus(refName) {
  const ref = useRef(refName);
  onMounted(() => {
    ref.el.focus();
  });
  return ref;
}
