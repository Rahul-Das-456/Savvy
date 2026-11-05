// Shared behaviour for the tool and study pages: section entrances, once, never leaving content hidden.
(() => {
  const groups = document.querySelectorAll(
    '.notes-wrap, .guide-wrap, .page-body, .scenario-wrap, .pillars, .sql-section, .setup-section, ' +
    '.terminal-section, .patterns-section, .arch-section, .viz-wrap, .ref-wrap, .back__card'
  );
  const targets = [];
  groups.forEach((group) => {
    Array.from(group.children).forEach((child, i) => {
      if (child.matches('script, style, [hidden]')) return;
      child.setAttribute('data-reveal', '');
      child.style.setProperty('--i', Math.min(i, 6));
      targets.push(child);
    });
  });
  if (!('IntersectionObserver' in window)) { targets.forEach((el) => el.classList.add('is-in')); return; }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-in');
      io.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
  targets.forEach((el) => io.observe(el));
  // anything already past the fold on load (deep links, restored scroll) shows at once
  setTimeout(() => targets.forEach((el) => { if (el.getBoundingClientRect().top < innerHeight) el.classList.add('is-in'); }), 50);
})();
