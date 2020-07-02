_open = false

function jumpToPhoto() {
	var url = new URL(window.location.href)
	var path = url.pathname
	var photo = path.match(/\/photo\/(\d+)$/)
	if (photo) {
		var idx = parseInt(photo[1], 10)
		$('.Collage').magnificPopup('open')
		$('.Collage').magnificPopup('goTo', idx - 1)		
	} else {
		$('.Collage').magnificPopup('close')
	}	
}

$(window).on('popstate',  function(e) {
	if (!e.originalEvent.state) return;
	jumpToPhoto()
});

// All images need to be loaded for this plugin to work so
// we end up waiting for the whole window to load in this example
$(window).on('load', function () {
    $(document).ready(function(){
	var url = new URL(window.location.href)
	var path = url.pathname
	var basepath = path.replace(/photo\/\d+$/, '')
	$('.spinner').hide();
        collage();
        $('.Collage').collageCaption();
        $('.Collage').magnificPopup({
		delegate: 'a',
		type: 'image',
		gallery:{
			enabled:true,
			tCounter: '<div class="mfp-counter">%curr% sur %total%</div>'
		},
		image: {
			titleSrc: function(item) {
				return item.el.attr('title') + 
				'<span class="img-dl"> &middot; <a class="image-source-link" href="'+
				item.el.attr('data-source')+
				'" target="_blank" title="Télécharger le grand format">grand format</a></span>';
			}
		},
		callbacks: {
			change: function() { 
				var idx = this.currItem.index + 1
				//console.log('change', idx)
				history.pushState('pushed', 'Photo ' + idx, basepath + 'photo/' + idx)
			},
			close:  function() {
				_open = false
				history.pushState('pushed', document.title, basepath)
			},
			open:   function() {
				_open = true
			},
		},
		mainClass: 'mfp-with-zoom mfp-img-mobile',
		zoom: {
			enabled: true,
			duration: 300, // don't forget to change the duration also in CSS
			easing: 'ease-in-out',
			opener: function(element) {
				return element.find('img');
			}
		},
	});
	jumpToPhoto();	
    });
})


// Here we apply the actual CollagePlus plugin
function collage() {
    $('.Collage').removeWhitespace().collagePlus({
                'allowPartialLastRow' : true,
                'fadeSpeed'           : 200,
                'targetHeight'        : 290
    });
}

// This is just for the case that the browser window is resized
var resizeTimer = null;
// store the current dimensions to avoid resize events triggered by scroll on mobile
var width = $(window).width()
$(window).on('resize', function() {
    // check whether the width has changed (if not, it's probably 
    // a scroll triggering the resize event. And if not, well no biggie, 
    // changing the height needs not change the collage.
    if($(window).width() != width) {
	width = $(window).width()
        // hide all the images until we resize them
        $('.Collage a').css("opacity", 0);
        // set a timer to re-apply the plugin
        if (resizeTimer) clearTimeout(resizeTimer);
        resizeTimer = setTimeout(collage, 200);
    }
})

