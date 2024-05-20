import streamlit as st
import replicate
import os
import PyPDF2
import networkx as nx
import plotly.graph_objects as go

# Set API token
replicate_api = "r8_Jq6sxUgeb4b3u6W5jZoDLWqLtu3mwsX2FJILX"
os.environ['REPLICATE_API_TOKEN'] = replicate_api

# App title
st.set_page_config(page_title="Mind Map Generator")

# Sidebar for model and parameters
with st.sidebar:
    st.title('Mind Map Generator')
    st.subheader('Llama2 Model and Parameters')
    selected_model = st.selectbox('Choose a Llama2 model', ['Llama2-7B', 'Llama2-13B'], key='selected_model')
    llm = 'a16z-infra/llama7b-v2-chat:4f0a4744c7295c024a1de15e1a63c880d3da035fa1f49bfd344fe076074c8eea' if selected_model == 'Llama2-7B' else 'a16z-infra/llama13b-v2-chat:df7690f1994d94e96ad9d568eac121aecf50684a0b0963b25a41cc40061269e5'
    temperature = st.slider('Temperature', min_value=0.01, max_value=5.0, value=0.5, step=0.01)
    top_p = st.slider('Top P', min_value=0.01, max_value=1.0, value=0.9, step=0.01)
    max_length = st.slider('Max Length', min_value=32, max_value=512, value=256, step=8)

# File upload
uploaded_file = st.file_uploader("Choose a PDF or text file", type=["pdf", "txt"])

def split_text(text, max_length):
    words = text.split()
    return [" ".join(words[i:i + max_length]) for i in range(0, len(words), max_length)]

def clean_response(response):
    lines = response.split('\n')
    structure = []
    for line in lines:
        if ':' in line:
            structure.append(line)
    return '\n'.join(structure)

def draw_mind_map(graph):
    pos = nx.spring_layout(graph)
    edge_x = []
    edge_y = []

    for edge in graph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    node_text = []

    for node in graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition='top center',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            colorscale='YlGnBu',
            size=10,
            colorbar=dict(
                thickness=15,
                title='Node Connections',
                xanchor='left',
                titleside='right'
            ),
            line_width=2))

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title='Generated Mind Map',
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
    st.plotly_chart(fig)

if uploaded_file is not None:
    # Text extraction
    text = ""
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    else:
        text = uploaded_file.read().decode("utf-8")

    # Split text into manageable chunks
    text_chunks = split_text(text, 512)

    mind_map_structure = ""
    for chunk in text_chunks:
        prompt = f"Based on the following text, generate a structure for a mind map that captures the main points and their relationships. The mind map structure should include the root node (main topic), child nodes (subtopics), and their relationships (edges). Present the mind map structure in plain text, with each node and its child nodes indented appropriately:\n\n{chunk}"
        output = replicate.run(llm, input={"prompt": prompt, "temperature": temperature, "top_p": top_p, "max_length": max_length})
        mind_map_structure += clean_response("".join(output))

    # Display mind map structure
    st.subheader("Mind Map Structure")
    st.write(mind_map_structure)

    # Generate mind map from the structure
    mind_map = nx.DiGraph()
    lines = mind_map_structure.split("\n")
    if lines:
        root_node = lines[0].split(":")[1].strip()
        mind_map.add_node(root_node)
        parent_stack = [(root_node, 0)]

        for line in lines[1:]:
            line = line.rstrip()
            if line:
                level = line.count('\t')
                node_name = line.split(":")[1].strip()

                while parent_stack and parent_stack[-1][1] >= level:
                    parent_stack.pop()

                parent_node = parent_stack[-1][0] if parent_stack else root_node
                mind_map.add_node(node_name)
                mind_map.add_edge(parent_node, node_name)
                parent_stack.append((node_name, level))

    # Draw mind map
    st.subheader("Generated Mind Map")
    draw_mind_map(mind_map)
