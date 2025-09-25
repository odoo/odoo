/** @odoo-module **/

if (window.odoo_user_id && window.odoo_user_id !== "false") {
  function scheduleLogout() {
    const now = new Date();
    const logoutTime = new Date();

    logoutTime.setHours(12, 10, 0, 0);

    if (now > logoutTime) {
      logoutTime.setDate(logoutTime.getDate() + 1);
    }

    const timeUntilLogout = logoutTime.getTime() - now.getTime();

    setTimeout(() => {
      window.location.href = "/web/session/logout";
    }, timeUntilLogout);
  }

  scheduleLogout();
} else {
  console.log("Script de Logout no activado: no hay un usuario logueado.");
}
