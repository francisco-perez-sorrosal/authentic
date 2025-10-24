from pathlib import Path


def load_template(template_name: str, **kwargs) -> str:
    """Load and render HTML template with simple string replacement."""
    template_path = Path(__file__).parent / "static" / template_name
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple template rendering with string replacement
    for key, value in kwargs.items():
        if isinstance(value, list):
            # Handle tools list rendering
            if key == 'tools':
                tools_html = ""
                for tool in value:
                    tools_html += f"""
                    <div class="tool-item">
                        <div class="tool-name">🔧 {tool['name']}</div>
                        <div class="tool-description">{tool['description']}</div>
                    </div>
                    """
                content = content.replace("{% for tool in tools %}", "").replace("{% endfor %}", tools_html)
                continue
        
        content = content.replace("{{" + key + "}}", str(value))
    
    return content