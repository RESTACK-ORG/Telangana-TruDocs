import { useState, useEffect } from 'react'

// Fixed left sidebar (TruDocs-ui-v3), ported from Maharashtra-TruDocs'
// trudocs-state/frontend-shell-v3/src/components/layout/DesktopSidebar.jsx.
// Telangana is a single-state app, so the collapsible row is "Telangana"
// instead of a future multi-state switcher, but the toggle/expand behavior
// is kept identical for visual parity with the reference layout.
export default function DesktopSidebar({ types, activeView, onNavigate }) {
  const [expanded, setExpanded] = useState(true)

  useEffect(() => {
    if (activeView) setExpanded(true)
  }, [activeView])

  return (
    <aside className="sidebar sidebar-desktop">
      <nav className="sidebar-nav">
        <button
          type="button"
          className="sidebar-state-toggle"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
        >
          <i className="ti ti-map-pin" />
          <span>Telangana</span>
          <i className={`ti ti-chevron-down sidebar-state-chevron${expanded ? ' expanded' : ''}`} />
        </button>
        <div className="sidebar-state-summary">{types.length} tools · 33+ districts</div>

        {expanded && (
          <div className="sidebar-state-tools">
            {types.map((item) => (
              <button
                key={item.id}
                className={`sidebar-nav-item${activeView === item.id ? ' active' : ''}`}
                onClick={() => onNavigate(item.id)}
              >
                <i className={item.icon} />
                <span>{item.navLabel}</span>
              </button>
            ))}
          </div>
        )}
      </nav>

      <div className="sidebar-status">
        <span className="sidebar-status-dot" />
        <span>Telangana</span>
      </div>
    </aside>
  )
}
