import { TOOL_EXPLAINERS } from '../content/toolExplainers.js'

// SEO-style explainer content shown below a tool once it's selected (TruDocs-ui-v3),
// ported from Maharashtra-TruDocs' components/common/ToolExplainer.jsx.
export default function ToolExplainer({ toolId }) {
  const data = TOOL_EXPLAINERS[toolId]
  if (!data) return null

  return (
    <div className="tool-explainer">
      <section className="tool-explainer-section">
        <h2 className="tool-explainer-heading">Overview</h2>
        <p className="tool-explainer-body">{data.overview}</p>
      </section>

      <section className="tool-explainer-section">
        <h2 className="tool-explainer-heading">What a {data.name} can show</h2>
        <p className="tool-explainer-body">{data.whatItShows}</p>
      </section>

      <section className="tool-explainer-section">
        <h2 className="tool-explainer-heading">Why it&rsquo;s hard to find on the government portal?</h2>
        <ul className="tool-explainer-list">
          {data.whyHard.map((point, i) => <li key={i}>{point}</li>)}
        </ul>
      </section>
    </div>
  )
}
