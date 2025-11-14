#!/usr/bin/env python3
"""
Statechart Diagram Generator
Generates an HTML/CSS page with nested statechart diagrams from a JSON design file.
"""

import json
import sys
import os
from typing import Dict, List, Tuple, Optional


class StatechartGenerator:
    """Generates HTML/CSS visualization of statechart diagrams from JSON."""
    
    def __init__(self, json_file: str):
        """Initialize the generator with a JSON design file."""
        self.json_file = json_file
        self.nodes = []
        self.edges = []
        self.node_map = {}  # Map node IDs to node data
        self.load_design()
        
    def load_design(self):
        """Load the design from JSON file."""
        try:
            with open(self.json_file, 'r') as f:
                data = json.load(f)
                self.nodes = data.get('nodes', [])
                self.edges = data.get('edges', [])
                
            # Create a map of node IDs to node data
            for node in self.nodes:
                self.node_map[node['id']] = node
                
        except FileNotFoundError:
            print(f"Error: File '{self.json_file}' not found.")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in '{self.json_file}': {e}")
            sys.exit(1)
            
    def get_node_hierarchy(self) -> Dict:
        """Build a hierarchy of nodes based on parent-child relationships."""
        hierarchy = {
            'root': [],
            'children': {}
        }
        
        for node in self.nodes:
            node_id = node['id']
            parent_id = node.get('parent_id')
            
            if parent_id is None:
                hierarchy['root'].append(node)
            else:
                if parent_id not in hierarchy['children']:
                    hierarchy['children'][parent_id] = []
                hierarchy['children'][parent_id].append(node)
                
        return hierarchy
    
    def get_node_edges(self, node_id: int) -> Tuple[List, List]:
        """Get incoming and outgoing edges for a node."""
        incoming = []
        outgoing = []
        
        for edge in self.edges:
            if edge['start_node_id'] == node_id:
                outgoing.append(edge)
            if edge['end_node_id'] == node_id:
                incoming.append(edge)
                
        return incoming, outgoing
    
    def calculate_absolute_position(self, node: Dict) -> Tuple[float, float]:
        """Calculate the absolute position of a node considering parent positions."""
        x = node['pos']['x']
        y = node['pos']['y']
        
        parent_id = node.get('parent_id')
        while parent_id is not None:
            parent = self.node_map.get(parent_id)
            if parent:
                x += parent['pos']['x']
                y += parent['pos']['y']
                # Add offset for parent's title bar (approximately 30px)
                y += 30
                parent_id = parent.get('parent_id')
            else:
                break
                
        return x, y
    
    def generate_svg_arrow(self, edge: Dict) -> str:
        """Generate SVG path for an edge with arrow using orthogonal routing."""
        start_node = self.node_map.get(edge['start_node_id'])
        end_node = self.node_map.get(edge['end_node_id'])
        
        if not start_node or not end_node:
            return ""
        
        # Calculate absolute positions of nodes
        start_node_x, start_node_y = self.calculate_absolute_position(start_node)
        end_node_x, end_node_y = self.calculate_absolute_position(end_node)
        
        # Add offsets from edge data to get actual connection points
        start_x = start_node_x + edge['start_offset']['x']
        start_y = start_node_y + edge['start_offset']['y']
        end_x = end_node_x + edge['end_offset']['x']
        end_y = end_node_y + edge['end_offset']['y']
        
        # Get waypoint ratio (controls position of vertical segment)
        waypoint_ratio = edge.get('waypoint_ratio', 0.5)
        
        # Calculate the X position of the vertical segment based on waypoint_ratio
        # waypoint_ratio of 0.5 means halfway between start and end X
        waypoint_x = start_x + (end_x - start_x) * waypoint_ratio
        
        # Determine which side of the end node the connection point is on
        # This helps us ensure the arrow points perpendicular to the border
        end_node_center_x = end_node_x + end_node['rect']['width'] / 2
        end_node_center_y = end_node_y + end_node['rect']['height'] / 2
        
        # Calculate relative position of connection point to node center
        rel_x = end_x - end_node_center_x
        rel_y = end_y - end_node_center_y
        
        # Determine which side: compare absolute distances
        end_node_width = end_node['rect']['width']
        end_node_height = end_node['rect']['height']
        
        # Normalize to determine which edge we're closest to
        norm_x = abs(rel_x) / (end_node_width / 2) if end_node_width > 0 else 0
        norm_y = abs(rel_y) / (end_node_height / 2) if end_node_height > 0 else 0
        
        # Create orthogonal path
        path_parts = []
        path_parts.append(f'M {start_x},{start_y}')  # Move to start
        
        # Determine if we should approach horizontally or vertically based on which border we're connecting to
        if norm_x > norm_y:
            # Connecting to left or right side - approach horizontally
            # Path: start -> horizontal to waypoint_x -> vertical to end_y -> horizontal to end_x
            path_parts.append(f'L {waypoint_x},{start_y}')  # Horizontal to waypoint
            path_parts.append(f'L {waypoint_x},{end_y}')    # Vertical to end Y level
            path_parts.append(f'L {end_x},{end_y}')         # Horizontal to end (arrow points horizontally)
        else:
            # Connecting to top or bottom side - approach vertically
            # Path: start -> horizontal to waypoint_x -> vertical to end_y
            path_parts.append(f'L {waypoint_x},{start_y}')  # Horizontal to waypoint
            path_parts.append(f'L {waypoint_x},{end_y}')    # Vertical to end (arrow points vertically)
            # If we need to adjust horizontally to reach end_x, do it before the final vertical segment
            if abs(end_x - waypoint_x) > 1:
                # Need to adjust path to end at correct X position
                path_parts.append(f'L {end_x},{end_y}')
        
        path = ' '.join(path_parts)
        
        # Calculate label position based on the longest segment
        # Find the longest segment to place the label on
        seg1_len = abs(waypoint_x - start_x)  # First horizontal segment
        seg2_len = abs(end_y - start_y)        # Vertical segment
        seg3_len = abs(end_x - waypoint_x)     # Last horizontal/vertical segment
        
        # Determine which segment is longest and position label accordingly
        if seg2_len >= seg1_len and seg2_len >= seg3_len:
            # Vertical segment is longest - place label to the side
            label_x = waypoint_x + 15  # Offset to the right of the vertical line
            label_y = (start_y + end_y) / 2
            text_anchor = "start"  # Left-aligned
        elif seg1_len >= seg3_len:
            # First horizontal segment is longest - place label above
            label_x = (start_x + waypoint_x) / 2
            label_y = start_y - 10
            text_anchor = "middle"
        else:
            # Last segment is longest
            if norm_x > norm_y:
                # Horizontal segment - place label above
                label_x = (waypoint_x + end_x) / 2
                label_y = end_y - 10
                text_anchor = "middle"
            else:
                # Vertical segment - place label to the side
                label_x = waypoint_x + 15
                label_y = (start_y + end_y) / 2
                text_anchor = "start"
        
        # Generate unique ID for this edge
        edge_id = f"edge_{edge['start_node_id']}_{edge['end_node_id']}"
        
        svg = f'''
        <g class="edge" id="{edge_id}" style="pointer-events: all;">
            <path d="{path}" class="edge-path" fill="none" stroke="#aaddff" stroke-width="2" marker-end="url(#arrowhead)" style="opacity: 1;"/>
            <text class="edge-label" x="{label_x}" y="{label_y}" text-anchor="{text_anchor}" fill="#ddd" font-size="12" style="pointer-events: none;">
                {edge.get('title', '')}
            </text>
        </g>
        '''
        
        return svg
    
    def generate_node_svg(self, node: Dict, depth: int = 0) -> str:
        """Generate SVG for a single node and its children."""
        node_id = node['id']
        title = node['title']
        pos_x, pos_y = self.calculate_absolute_position(node)
        width = node['rect']['width']
        height = node['rect']['height']
        node_type = node.get('node_type', 'State')
        is_container = node.get('is_container', False)
        is_initial = node.get('is_initial', False)
        
        # Determine node color based on type
        if node_type == 'StateMachine':
            fill_color = '#3a4a5a'
            stroke_color = '#5a7a9a'
            title_color = '#88ccff'
        elif node_type == 'State':
            fill_color = '#2a3a4a'
            stroke_color = '#4a6a8a'
            title_color = '#aaddff'
        else:
            fill_color = '#2a2a3a'
            stroke_color = '#4a4a6a'
            title_color = '#ccccff'
        
        # Add initial state indicator
        initial_marker = ''
        if is_initial:
            # Position circle on the right side of title bar, 10px from right edge
            # Title bar is 30px high (from pos_y to pos_y + 30), so center is at pos_y + 15
            circle_x = pos_x + width - 10 - 10  # 10px from right edge, minus 10px radius
            circle_y = pos_y + 15  # Vertically centered in title bar
            initial_marker = f'''
            <circle cx="{circle_x}" cy="{circle_y}" r="10" fill="white" stroke="#888" stroke-width="2" style="opacity: 1;"/>
            '''
        
        svg = f'''
        <g class="node node-{node_type.lower()}" id="node_{node_id}" data-depth="{depth}">
            <rect x="{pos_x}" y="{pos_y}" width="{width}" height="{height}" 
                  fill="{fill_color}" stroke="{stroke_color}" stroke-width="2" rx="5"/>
            <text x="{pos_x + 10}" y="{pos_y + 20}" fill="{title_color}" font-size="14" font-weight="bold">
                {title}
            </text>
            <line x1="{pos_x}" y1="{pos_y + 30}" x2="{pos_x + width}" y2="{pos_y + 30}" 
                  stroke="{stroke_color}" stroke-width="1"/>
            {initial_marker}
        '''
        
        # Add children if this is a container
        if is_container:
            hierarchy = self.get_node_hierarchy()
            children = hierarchy['children'].get(node_id, [])
            for child in children:
                svg += self.generate_node_svg(child, depth + 1)
        
        svg += '</g>\n'
        
        return svg
    
    def generate_html(self, output_file: str):
        """Generate the complete HTML file with embedded CSS and SVG."""
        hierarchy = self.get_node_hierarchy()
        root_nodes = hierarchy['root']
        
        # Calculate SVG dimensions
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for node in self.nodes:
            abs_x, abs_y = self.calculate_absolute_position(node)
            min_x = min(min_x, abs_x)
            min_y = min(min_y, abs_y)
            max_x = max(max_x, abs_x + node['rect']['width'])
            max_y = max(max_y, abs_y + node['rect']['height'])
        
        # Add padding
        padding = 100
        min_x -= padding
        min_y -= padding
        max_x += padding
        max_y += padding
        
        svg_width = max_x - min_x
        svg_height = max_y - min_y
        
        # Generate SVG content
        svg_nodes = ''
        for root_node in root_nodes:
            svg_nodes += self.generate_node_svg(root_node)
        
        svg_edges = ''
        for edge in self.edges:
            svg_edges += self.generate_svg_arrow(edge)
        
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Statechart Diagram - {os.path.basename(self.json_file)}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 100%;
            margin: 0 auto;
        }}
        
        h1 {{
            text-align: center;
            margin-bottom: 30px;
            color: #88ccff;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        }}
        
        .diagram-container {{
            background: #0f1419;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            overflow: auto;
        }}
        
        svg {{
            display: block;
            margin: 0 auto;
            background: #1a1f26;
            border-radius: 5px;
        }}
        
        .node {{
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .node:hover rect {{
            filter: brightness(1.2);
        }}
        
        .edge {{
            opacity: 1 !important;
            pointer-events: all;
        }}
        
        .edge-path {{
            transition: all 0.3s ease;
            opacity: 1 !important;
            stroke: #aaddff !important;
        }}
        
        .edge:hover .edge-path {{
            stroke: #ffaa44;
            stroke-width: 3;
        }}
        
        .edge:hover .edge-label {{
            fill: #ffaa44;
            font-weight: bold;
        }}
        
        .info-panel {{
            background: #1a2332;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            border: 1px solid #3a4a5a;
        }}
        
        .info-panel h2 {{
            color: #88ccff;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        
        .info-panel ul {{
            list-style: none;
            padding-left: 0;
        }}
        
        .info-panel li {{
            padding: 8px 0;
            border-bottom: 1px solid #2a3a4a;
            color: #aaddff;
        }}
        
        .info-panel li:last-child {{
            border-bottom: none;
        }}
        
        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .legend-box {{
            width: 30px;
            height: 20px;
            border-radius: 3px;
            border: 2px solid;
        }}
        
        .legend-statemachine {{
            background: #3a4a5a;
            border-color: #5a7a9a;
        }}
        
        .legend-state {{
            background: #2a3a4a;
            border-color: #4a6a8a;
        }}
        
        .legend-initial {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #88ff88;
            border-color: #44aa44;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            h1 {{
                font-size: 1.5em;
            }}
            
            .legend {{
                flex-direction: column;
                align-items: flex-start;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔄 Statechart Diagram</h1>
        
        <div class="diagram-container">
            <svg width="{svg_width}" height="{svg_height}" viewBox="{min_x} {min_y} {svg_width} {svg_height}">
                <defs>
                    <!-- Arrow marker for edges -->
                    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
                        <polygon points="0 0, 10 3, 0 6" fill="#aaddff"/>
                    </marker>
                    <!-- Arrow marker for initial state -->
                    <marker id="arrowhead-initial" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                        <polygon points="0 0, 10 3, 0 6" fill="#44aa44"/>
                    </marker>
                </defs>
                
                <!-- Nodes (drawn first) -->
                {svg_nodes}
                
                <!-- Edges (drawn last so they appear on top) -->
                {svg_edges}
            </svg>
        </div>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-box legend-statemachine"></div>
                <span>State Machine</span>
            </div>
            <div class="legend-item">
                <div class="legend-box legend-state"></div>
                <span>State</span>
            </div>
            <div class="legend-item">
                <div class="legend-box legend-initial"></div>
                <span>Initial State</span>
            </div>
        </div>
        
        <div class="info-panel">
            <h2>📊 Diagram Statistics</h2>
            <ul>
                <li><strong>Total Nodes:</strong> {len(self.nodes)}</li>
                <li><strong>Total Transitions:</strong> {len(self.edges)}</li>
                <li><strong>State Machines:</strong> {sum(1 for n in self.nodes if n.get('node_type') == 'StateMachine')}</li>
                <li><strong>States:</strong> {sum(1 for n in self.nodes if n.get('node_type') == 'State')}</li>
                <li><strong>Container States:</strong> {sum(1 for n in self.nodes if n.get('is_container'))}</li>
                <li><strong>Initial States:</strong> {sum(1 for n in self.nodes if n.get('is_initial'))}</li>
            </ul>
        </div>
    </div>
    
    <script>
        // Add interactivity
        document.querySelectorAll('.node').forEach(node => {{
            node.addEventListener('click', function() {{
                const nodeId = this.id;
                console.log('Clicked node:', nodeId);
                
                // Highlight the node
                this.style.opacity = this.style.opacity === '0.7' ? '1' : '0.7';
            }});
        }});
        
        // Add hover effects for edges
        document.querySelectorAll('.edge').forEach(edge => {{
            edge.addEventListener('mouseenter', function() {{
                this.style.opacity = '1';
            }});
            
            edge.addEventListener('mouseleave', function() {{
                this.style.opacity = '0.8';
            }});
        }});
    </script>
</body>
</html>'''
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"✅ Successfully generated: {output_file}")
        print(f"📊 Nodes: {len(self.nodes)}, Edges: {len(self.edges)}")


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python generate_statechart.py <input.json> [output.html]")
        print("\nExample:")
        print("  python generate_statechart.py design5.json")
        print("  python generate_statechart.py design5.json output.html")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Determine output file name
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        # Generate output filename from input filename
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_statechart.html"
    
    # Generate the statechart
    generator = StatechartGenerator(input_file)
    generator.generate_html(output_file)
    
    print(f"\n🌐 Open the file in your browser to view the diagram:")
    print(f"   file://{os.path.abspath(output_file)}")


if __name__ == "__main__":
    main()
