/** @odoo-module **/

document.addEventListener("DOMContentLoaded", () => {
  if (localStorage.getItem("openInKioskMode") === "true") {
    localStorage.removeItem("openInKioskMode");

    const observer = new MutationObserver((mutationsList, obs) => {
      const odooApp = document.querySelector(".o_action_manager");
      if (odooApp) {
        console.log("Odoo App detectada. Activando modo kiosko y esperando al botón de guardado.");
        document.body.classList.add("kiosk-mode");

        
        const maxTries = 20; 
        let tries = 0;
        const findSaveButtonInterval = setInterval(() => {
            const saveButton = document.querySelector(".o_form_button_save");
            if (saveButton) {
                clearInterval(findSaveButtonInterval);
                console.log("Botón de Guardar encontrado. Adjuntando evento de clic.");
                
                saveButton.addEventListener("click", function () {
                    console.log("Botón de Guardar presionado. Enviando señal...");
                    localStorage.setItem("profileSaveClicked", "true");
                });
            }

            tries++;
            if (tries > maxTries) {
                clearInterval(findSaveButtonInterval);
                console.error("No se encontró el botón de Guardar después de 5 segundos.");
            }
        }, 250); 
        
        observer.disconnect();
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }
});