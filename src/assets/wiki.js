(function(){
  "use strict";
  var body=document.body;

  /* Menú móvil */
  var btn=document.querySelector(".menu-btn");
  if(btn){btn.addEventListener("click",function(){
    var o=body.classList.toggle("open");btn.setAttribute("aria-expanded",o?"true":"false");
  });}
  document.querySelectorAll(".side a").forEach(function(a){
    a.addEventListener("click",function(){body.classList.remove("open");if(btn)btn.setAttribute("aria-expanded","false");});
  });

  /* Copiar bloques de código y prompts */
  document.querySelectorAll(".copy").forEach(function(b){
    b.addEventListener("click",function(){
      var pre=b.closest(".code,.prompt").querySelector("pre");
      var txt=pre.innerText;
      var done=function(){var t=b.textContent;b.textContent="¡Copiado!";setTimeout(function(){b.textContent=t;},1400);};
      if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(txt).then(done,function(){fallback(txt);done();});}
      else{fallback(txt);done();}
    });
  });
  function fallback(t){var x=document.createElement("textarea");x.value=t;x.style.position="fixed";x.style.opacity="0";document.body.appendChild(x);x.select();try{document.execCommand("copy");}catch(e){}document.body.removeChild(x);}

  /* Pestañas */
  document.querySelectorAll(".tabs").forEach(function(t){
    var btns=t.querySelectorAll(".tablist button"),panels=t.querySelectorAll(".tabpanel");
    function sel(i,focus){
      btns.forEach(function(b,j){b.setAttribute("aria-selected",j===i?"true":"false");b.tabIndex=j===i?0:-1;});
      panels.forEach(function(p,j){p.classList.toggle("on",j===i);});
      if(focus)btns[i].focus();
    }
    btns.forEach(function(b,i){
      b.addEventListener("click",function(){sel(i,false);});
      b.addEventListener("keydown",function(e){
        if(e.key==="ArrowRight"){sel((i+1)%btns.length,true);e.preventDefault();}
        if(e.key==="ArrowLeft"){sel((i-1+btns.length)%btns.length,true);e.preventDefault();}
      });
    });
    sel(0,false);
  });

  /* Abrir el <details> de destino si llega un #ancla */
  function openHash(){
    var id=location.hash.slice(1);if(!id)return;
    var el=document.getElementById(id);
    if(el){var d=el.closest("details");if(d)d.open=true;}
  }
  window.addEventListener("hashchange",openHash);openHash();

  /* Scrollspy de la tabla de contenidos de la página */
  var links=[].slice.call(document.querySelectorAll(".nav ul a"));
  if(links.length&&"IntersectionObserver" in window){
    var map={};links.forEach(function(a){map[a.getAttribute("href").split("#")[1]]=a;});
    var io=new IntersectionObserver(function(es){
      es.forEach(function(e){
        if(e.isIntersecting){links.forEach(function(l){l.classList.remove("on");});var a=map[e.target.id];if(a)a.classList.add("on");}
      });
    },{rootMargin:"-90px 0px -70% 0px"});
    Object.keys(map).forEach(function(id){var h=document.getElementById(id);if(h)io.observe(h);});
  }

  /* Búsqueda local */
  var q=document.getElementById("q"),res=document.getElementById("results"),nav=document.querySelector(".nav");
  var IDX=window.WIKI_INDEX||[];
  function norm(s){return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"");}
  if(q){q.addEventListener("input",function(){
    var v=norm(q.value.trim());
    if(v.length<2){res.classList.remove("on");res.innerHTML="";nav.style.display="";return;}
    var terms=v.split(/\s+/);
    var hits=IDX.map(function(d){
      var hay=norm(d.t+" "+d.x),sc=0;
      for(var i=0;i<terms.length;i++){
        if(hay.indexOf(terms[i])<0)return null;
        if(norm(d.t).indexOf(terms[i])>=0)sc+=5;sc+=1;
      }
      return {d:d,sc:sc};
    }).filter(Boolean).sort(function(a,b){return b.sc-a.sc;}).slice(0,8);
    nav.style.display="none";res.classList.add("on");res.innerHTML="";
    if(!hits.length){var li=document.createElement("li");li.innerHTML='<a href="#" tabindex="-1">Sin resultados</a>';res.appendChild(li);return;}
    hits.forEach(function(h){
      var li=document.createElement("li"),a=document.createElement("a");
      a.href=h.d.u;a.textContent=h.d.t;
      var s=document.createElement("small");s.textContent=h.d.p;a.appendChild(s);
      li.appendChild(a);res.appendChild(li);
    });
  });}
})();
