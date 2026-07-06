import streamlit as st
import redis
import pymongo
from neo4j import GraphDatabase
import requests
import json
import time
import random
from pyvis.network import Network
import streamlit.components.v1 as components

# ==========================================
# 1. SETUP & POLYGLOT DATABASE CONNECTIONS
# ==========================================
st.set_page_config(page_title="Misinfo Spread & Backtrack Engine", layout="wide", page_icon="🕸️")

@st.cache_resource
def init_dbs():
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = mongo_client["misinfo_db"]
        posts_collection = db["posts"]
        # UPDATE THIS PASSWORD TO MATCH YOUR NEO4J INSTANCE
        neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "harsh@neo4j"))
        return r, posts_collection, neo4j_driver
    except Exception as e:
        st.error(f"Database Connection Error. Are Redis, Mongo, and Neo4j running? {e}")
        return None, None, None

r, posts_collection, neo4j_driver = init_dbs()
OLLAMA_URL = "http://localhost:11434/api/generate"

# ==========================================
# 2. CORE SIMULATION & AI FUNCTIONS
# ==========================================
def reset_databases():
    """Clears all databases to start fresh."""
    r.flushdb()
    posts_collection.delete_many({})
    with neo4j_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

def create_base_network(num_users):
    """Creates a proper social web of Humans (fixes the single thread issue)."""
    with neo4j_driver.session() as session:
        # 1. Create Normal Humans
        for i in range(1, num_users + 1):
            session.run("MERGE (u:User {id: $id, type: 'Human'})", id=f"human_{i}")
            
        # 2. Create a realistic social web (each user follows 2-4 random people)
        session.run("""
            MATCH (u:User {type: 'Human'})
            WITH collect(u) as users
            UNWIND users as u1
            WITH u1, users, toInteger(rand() * 3) + 2 as num_follows
            UNWIND range(1, num_follows) as i
            WITH u1, users[toInteger(rand() * size(users))] as u2
            WHERE u1.id <> u2.id
            MERGE (u1)-[:FOLLOWS]->(u2)
        """)

def analyze_with_ollama(text):
    """Asks local Llama to grade text, using Redis to cache previous analyses."""
    cache_key = f"tweet_analysis:{hash(text)}"
    cached_result = r.get(cache_key)
    if cached_result:
        return json.loads(cached_result)

    prompt = f"""
    Analyze this social media post for misinformation. 
    1. Give it a suspicion score from 0.0 (normal) to 1.0 (highly fake/conspiracy). 
    2. Extract a 1 to 3 word narrative category (e.g., "Deepfake Audio", "Health Scare").
    3. Identify the Primary Emotion.
    Post: "{text}"
    Respond ONLY in strict JSON format. Example: {{"score": 0.9, "narrative": "Deepfake Video", "emotion": "Fear"}}
    """
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }).json()
        result = json.loads(response['response'])
        r.setex(cache_key, 3600, json.dumps(result))
        return result
    except Exception as e:
        return {"score": 0.8, "narrative": "Suspicious Media", "emotion": "Alarm"}

def inject_viral_cascade(post_id, poster_name, text, is_influencer, bot_count):
    """Simulates the chronological spread with a dynamically sized bot swarm."""
    poster_id = poster_name.strip().replace(" ", "_").lower()
    poster_type = "Influencer" if is_influencer else "Human"
    
    with neo4j_driver.session() as session:
        # 1. Create Poster and Post at Time = 0
        session.run("""
            MERGE (u:User {id: $poster_id, type: $poster_type})
            MERGE (p:Post {id: $post_id, text: $text, status: 'Active'})
            MERGE (u)-[:POSTED {time: 0}]->(p)
        """, poster_id=poster_id, poster_type=poster_type, post_id=post_id, text=text)
        
        # Connect poster loosely to the network
        session.run("""
            MATCH (u:User {id: $poster_id}), (h:User {type: 'Human'})
            WITH u, h ORDER BY rand() LIMIT 5
            MERGE (h)-[:FOLLOWS]->(u)
        """, poster_id=poster_id)

        # 2. Early Organic Sharing (Time 1-3)
        session.run("""
            MATCH (follower:User)-[:FOLLOWS]->(poster:User {id: $poster_id}), (p:Post {id: $post_id})
            WHERE rand() > 0.2
            MERGE (follower)-[:RETWEETED {time: toInteger(rand() * 3) + 1}]->(p)
        """, poster_id=poster_id, post_id=post_id)

        # 3. Create and Activate Bot Swarm (Time 4-6)
        bot_ids = [f"bot_{random.randint(1000, 9999)}" for _ in range(bot_count)]
        for bot_id in bot_ids:
            # Bot Retweets
            session.run("""
                MERGE (b:User {id: $bot_id, type: 'Bot'})
                WITH b
                MATCH (p:Post {id: $post_id})
                MERGE (b)-[:RETWEETED {time: toInteger(rand() * 3) + 4}]->(p)
            """, bot_id=bot_id, post_id=post_id)
            
            # Bot follows random humans to infiltrate
            session.run("""
                MATCH (b:User {id: $bot_id}), (h:User {type: 'Human'})
                WITH b, h ORDER BY rand() LIMIT 2
                MERGE (b)-[:FOLLOWS]->(h)
            """, bot_id=bot_id)

        # 4. Viral Cascade (Time 7-10)
        session.run("""
            MATCH (victim:User)-[:FOLLOWS]->(spreader:User)-[r:RETWEETED]->(p:Post {id: $post_id})
            WHERE victim <> spreader AND NOT (victim)-[:RETWEETED]->(p) AND rand() > 0.3
            MERGE (victim)-[:RETWEETED {time: toInteger(rand() * 4) + 7}]->(p)
        """, post_id=post_id)

    return poster_id

def generate_graph_html(current_time):
    """Generates the clean, hoverable graph."""
    net = Network(height="700px", width="100%", bgcolor="#111111", font_color="white")
    
    # Physics to cluster network nicely
    net.force_atlas_2based(central_gravity=0.015, spring_length=150, spring_strength=0.08, damping=0.9, overlap=0)
    
    with neo4j_driver.session() as session:
        # Determine active nodes up to current_time
        query = "MATCH (n)-[r]->(m) RETURN n, type(r) as rel_type, r.time as time, m"
        results = session.run(query)
        
        active_nodes = set()
        for record in results:
            n, rel_type, r_time, m = record["n"], record["rel_type"], record["time"], record["m"]
            # Always show the post, humans, and active retweets
            if "Post" in n.labels or "Post" in m.labels:
                active_nodes.add(n["id"])
                active_nodes.add(m["id"])
            if rel_type in ['POSTED', 'RETWEETED'] and r_time is not None and r_time <= current_time:
                active_nodes.add(n["id"])
                active_nodes.add(m["id"])
            if rel_type == 'FOLLOWS': # Keep follows visible but muted later
                active_nodes.add(n["id"])
                active_nodes.add(m["id"])

        results = session.run(query)
        added_nodes = set()

        for record in results:
            node1, rel_type, r_time, node2 = record["n"], record["rel_type"], record["time"], record["m"]
            
            def add_node_to_net(n):
                n_id = n["id"]
                if n_id in added_nodes: return
                added_nodes.add(n_id)
                
                labels = list(n.labels)
                is_active_spreader = n_id in active_nodes
                
                if "User" in labels:
                    if not is_active_spreader: color = "#333333" 
                    elif n.get("type") == "Bot": color = "#ff2a2a" 
                    elif n.get("type") == "Influencer": color = "#bd4bff" 
                    else: color = "#2a8bff" 
                    net.add_node(n_id, label=n_id, color=color, size=15)
                
                elif "Post" in labels:
                    # Make the post very obvious
                    if n.get("status") == "QUARANTINED":
                        net.add_node(n_id, label="🛡️ QUARANTINED POST", color="#555555", size=50, shape="star")
                    else:
                        net.add_node(n_id, label="📰 TARGET POST", color="#ffaa00", size=50, shape="star")

            add_node_to_net(node1)
            add_node_to_net(node2)
            
            # EDGE FORMATTING
            if rel_type == "FOLLOWS":
                net.add_edge(node1["id"], node2["id"], color="#444444", dashes=True, value=0.5, title="Follows")
            elif rel_type == "POSTED" and r_time is not None and r_time <= current_time:
                net.add_edge(node1["id"], node2["id"], title="ORIGINAL POST", color="#ffaa00", value=4)
            elif rel_type == "RETWEETED" and r_time is not None and r_time <= current_time:
                edge_color = "#ff2a2a" if "bot" in node1["id"] else "#ffaa00"
                net.add_edge(node1["id"], node2["id"], title="RETWEETED", color=edge_color, value=2)

    net.save_graph("neo4j_graph.html")
    return "neo4j_graph.html"

# ==========================================
# 3. STREAMLIT UI LAYOUT
# ==========================================

# --- SESSION STATE INITIALIZATION ---
if "db_initialized" not in st.session_state:
    reset_databases()
    st.session_state.db_initialized = True
    st.session_state.post_id = None
    st.session_state.poster_id = None
    st.session_state.deployed = False
    st.session_state.time_step = 0
    create_base_network(40)

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("🌐 Global Network Setup")
st.sidebar.markdown("Define your baseline 'normal' network before launching an attack.")
num_users_input = st.sidebar.slider("Number of Normal Users", 10, 150, 40)

if st.sidebar.button("🔄 Generate Base Network", use_container_width=True):
    reset_databases()
    create_base_network(num_users_input)
    st.session_state.deployed = False
    st.session_state.time_step = 0
    st.rerun()

st.title("🕸️ Misinformation Spread & Backtrack Engine")

col1, col2 = st.columns([1.2, 1.8])

with col1:
    # Initialize session states for our buttons
    if "analysis_triggered" not in st.session_state:
        st.session_state.analysis_triggered = False
    if "manual_spike" not in st.session_state:
        st.session_state.manual_spike = False

    st.header("1. Threat Injection")
    st.markdown("Simulate a deepfake or fake news injection into the network.")
    
    poster_name = st.text_input("Poster Username:", value="Anon_Patriot_99")
    is_influencer = st.checkbox("✅ Verified Official Account")
    fake_news_text = st.text_area("Post Content:", value="[DEEPFAKE VIDEO ATTACHED] The CEO just admitted the water supply is poisoned! Do not drink the tap water! #Conspiracy")
    bot_count_input = st.slider("🤖 Number of Bots in Swarm", 5, 100, 20)
    
    if st.button("🚨 DEPLOY NARRATIVE TO NETWORK", use_container_width=True):
        with st.spinner("Calculating viral cascade..."):
            post_id = f"post_{int(time.time())}"
            st.session_state.post_id = post_id
            st.session_state.poster_id = inject_viral_cascade(post_id, poster_name, fake_news_text, is_influencer, bot_count_input)
            st.session_state.deployed = True
            st.session_state.text = fake_news_text
            # Reset all demo states on a new deployment
            st.session_state.time_step = 0
            st.session_state.analysis_triggered = False
            st.session_state.manual_spike = False
        st.rerun()

    if st.session_state.deployed:
        st.markdown("---")
        st.header("2. Simulation Time Control")
        st.caption("Control the spread manually for your live demonstration.")
        
        # DEMO CONTROL BUTTONS
        btn_col1, btn_col2 = st.columns(2)
        if btn_col1.button("⏳ +1 Hour (Organic)", use_container_width=True):
            if st.session_state.time_step < 10:
                st.session_state.time_step += 1
                st.rerun()
                
        if btn_col2.button("🚀 TRIGGER VIRAL SPIKE", type="primary", use_container_width=True):
            st.session_state.time_step = 6  # Jump to hour 6 to capture the full bot swarm
            st.session_state.manual_spike = True # Guarantee the alarm triggers
            st.rerun()
        
        current_retweets = 0
        prev_retweets = 0
        # Fetch current and previous metrics from Neo4j, splitting by User Type
        with neo4j_driver.session() as session:
            # Get total from previous hour for velocity calculation
            prev_retweets = session.run("MATCH ()-[r:RETWEETED]->(p:Post {id: $pid}) WHERE r.time <= $time RETURN count(r) as c", pid=st.session_state.post_id, time=st.session_state.time_step-1).single()["c"]
            
            # Get current hour details grouped by bot vs human
            query = """
                MATCH (u:User)-[r:RETWEETED]->(p:Post {id: $pid}) 
                WHERE r.time <= $time 
                RETURN u.type as user_type, count(r) as c
            """
            results = session.run(query, pid=st.session_state.post_id, time=st.session_state.time_step)
            
            human_shares = 0
            bot_shares = 0
            for record in results:
                if record["user_type"] == "Bot":
                    bot_shares = record["c"]
                else:
                    human_shares += record["c"] # Groups normal Humans and the original Influencer
            
            current_retweets = human_shares + bot_shares
            velocity = current_retweets - prev_retweets

        # DISPLAY THE SPLIT METRICS
        st.markdown("#### 📊 Real-Time Spread Analytics")
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Total Shares (Hr {st.session_state.time_step})", current_retweets, delta=f"+{velocity}/hr velocity", delta_color="inverse" if velocity > 5 else "normal")
        
        # Calculate Bot Influence Percentage
        bot_percentage = int((bot_shares / current_retweets) * 100) if current_retweets > 0 else 0
        
        m2.metric("👤 Organic (Humans)", human_shares)
        m3.metric("🤖 Inorganic (Bots)", bot_shares, delta=f"{bot_percentage}% of spread", delta_color="inverse" if bot_percentage > 40 else "normal")
        
        st.metric(f"Current Time: Hour {st.session_state.time_step}", f"{current_retweets} Total Shares", delta=f"+{velocity} shares this hour", delta_color="inverse" if velocity > 5 else "normal")

        st.markdown("---")
        st.header("3. AI Detection & Backtracking")
        
        # Trigger condition: High velocity OR user clicked the spike button
        is_spike = velocity >= 5 or st.session_state.manual_spike
        
        # If spike happens OR user manually clicks the button, lock the analysis state to TRUE
        if is_spike or st.button("🔍 Force AI Analysis"):
            st.session_state.analysis_triggered = True

        # Render the analysis ONLY if the state is locked to true
        if st.session_state.analysis_triggered:
            if is_spike:
                st.error("⚠️ VELOCITY SPIKE DETECTED. Engine automatically intercepting payload...")
            
            analysis = analyze_with_ollama(st.session_state.text)
            score = analysis.get('score', 0)
            
            c1, c2 = st.columns(2)
            c1.metric("LLM Suspicion Score", f"{score}/1.0", delta="Fake Risk" if score > 0.6 else "Safe", delta_color="inverse")
            c2.metric("Extracted Narrative", analysis.get('narrative', 'Unknown'))
            
            if score >= 0.5:
                st.warning("🚨 MALICIOUS CONTENT CONFIRMED. Initiating Cypher Backtracking...")
                
                with neo4j_driver.session() as session:
                    source_record = session.run("""
                        MATCH (u:User)-[:POSTED]->(p:Post {id: $pid})
                        RETURN u.id as source_id, u.type as source_type
                    """, pid=st.session_state.post_id).single()
                
                if source_record:
                    src_id = source_record["source_id"]
                    src_type = source_record["source_type"]
                    
                    st.code(f"// NEO4J BACKTRACK EXECUTED\nMATCH (u:User)-[:POSTED]->(p:Post)\nRETURN u", language="cypher")
                    
                    if src_type == "Influencer":
                        st.info(f"🟢 **Trace Complete:** Patient Zero is `{src_id}`. Account is VERIFIED. Escalating to human moderator instead of auto-ban.")
                    else:
                        st.error(f"🔴 **Trace Complete:** Patient Zero is `{src_id}`. UNVERIFIED origin. Deepfake spread confirmed.")
                        
                        # Because this button is protected by st.session_state.analysis_triggered, it will now work!
                        if st.button("☣️ SEVER NETWORK & LOG TO MONGO", type="primary", use_container_width=True):
                            with neo4j_driver.session() as session:
                                session.run("MATCH (n)-[r:RETWEETED]->(p:Post {id: $pid}) DELETE r", pid=st.session_state.post_id)
                                session.run("MATCH (p:Post {id: $pid}) SET p.status = 'QUARANTINED'", pid=st.session_state.post_id)
                            
                            doc = {
                                "post_id": st.session_state.post_id,
                                "source_id": src_id,
                                "text": st.session_state.text,
                                "ai_analysis": analysis,
                                "spread_velocity_at_detection": velocity,
                                "status": "QUARANTINED",
                                "timestamp": time.time()
                            }
                            posts_collection.insert_one(doc)
                            st.success("Network severed. Evidence encrypted in MongoDB Ledger.")
                            
                            time.sleep(1.5)
                            st.session_state.time_step = 10 
                            # Reset states so the UI cleans up nicely
                            st.session_state.analysis_triggered = False 
                            st.session_state.manual_spike = False
                            st.rerun()

with col2:
    st.header("📡 Live Graph Topology")
    st.caption("✨ The Post is marked by a Star. Dashed lines are Follows. Solid lines are Shares.")
    
    if not st.session_state.deployed:
        graph_html = generate_graph_html(-1) 
    else:
        graph_html = generate_graph_html(st.session_state.time_step)
        
    with open(graph_html, 'r', encoding='utf-8') as f:
        components.html(f.read(), height=750)

    st.markdown("### 🗄️ MongoDB Threat Ledger (Historical Data)")
    recent_threats = list(posts_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(3))
    if recent_threats:
        for threat in recent_threats:
            with st.expander(f"🛡️ QUARANTINED: {threat['source_id']} - {threat['text'][:30]}..."):
                st.json(threat)
    else:
        st.info("No threats quarantined in MongoDB yet.")
