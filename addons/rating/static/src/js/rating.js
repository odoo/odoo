function changeRating() {
    var elements = document.querySelectorAll(".o_rating");
    elements.forEach(function(elem) {
        elem.addEventListener("click", function (event) {
            event.preventDefault();
            Array.prototype.forEach.call(document.getElementsByTagName('img'), function(element){
                element.removeAttribute('style');
            });
            event.currentTarget.firstElementChild.style.WebkitFilter = "drop-shadow(0 0 5px black)";
            var rate = document.getElementById("rate_id");
            rate.value= event.currentTarget.dataset.value;
        });
    });
};

document.addEventListener('DOMContentLoaded', function () {
    changeRating();
}, false);
