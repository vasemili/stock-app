// Your existing vanilla JavaScript code for the sidebar toggle
document.getElementById("sidebarToggle").addEventListener("click", function() {
    const sidebar = document.getElementById("sidebar");
    const body = document.querySelector('body');
    if (sidebar.style.left === "-250px") {
        sidebar.style.left = "0px";
        body.classList.add('sidebar-opened');
    } else {
        sidebar.style.left = "-250px";
        body.classList.remove('sidebar-opened');
    }
});
