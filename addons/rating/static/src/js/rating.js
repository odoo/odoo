function myFunction() {
    var elements = document.getElementsByClassName("o_rating");
    for(var i=0; i<elements.length; i++) {
        elements[i].addEventListener("click", function (event) {
            event.preventDefault();
            var img = document.getElementsByTagName('img');
            for (var j=0; j<img.length; j++){
                img[j].style.WebkitFilter = null;
            }
            event.currentTarget.firstElementChild.style.WebkitFilter = "drop-shadow(0 0 5px black)";
            var id = event.currentTarget.getAttribute('id');
            var rate = document.getElementById("rate_id");
            rate.value= id;
        });
    }
};

document.addEventListener('DOMContentLoaded', function () {
    myFunction();
}, false);
