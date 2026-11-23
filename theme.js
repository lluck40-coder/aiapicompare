// Heller/dunkler Modus – Auswahl wird im Browser gespeichert.
// Ohne eigene Wahl richtet sich die Seite nach der Systemeinstellung.
(function () {
  var d = document.documentElement;
  try {
    var t = localStorage.getItem("theme");
    if (!t && window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches) t = "light";
    if (t === "light") d.setAttribute("data-theme", "light");
  } catch (e) {}
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest(".themebtn");
    if (!b) return;
    var hell = d.getAttribute("data-theme") === "light";
    if (hell) d.removeAttribute("data-theme"); else d.setAttribute("data-theme", "light");
    try { localStorage.setItem("theme", hell ? "dark" : "light"); } catch (e2) {}
  });
})();
