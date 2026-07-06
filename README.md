1. Dataset Description
The system uses a synthetic, dynamically generated dataset simulating social media interactions. Data is stored across a polyglot architecture:
•	Neo4j (Graph DB): User network (nodes: Users, Posts; edges: FOLLOWS, POSTED, RETWEETED) 
•	MongoDB: Historical threat ledger (quarantined misinformation cases) 
•	Redis: Caching AI analysis results for performance 
Features:
•	User types (Human, Bot, Influencer) 
•	Temporal propagation (time-based retweets) 
•	Content attributes (text, narrative, emotion, suspicion score) 
Preprocessing:
•	Text normalization before AI analysis 
•	Graph structuring for propagation tracking 
•	Cached inference using Redis to avoid recomputation 
2. Problem Statement
Misinformation spreads rapidly through social networks, often amplified by bots and influencers. Existing systems lack:
•	Real-time detection of viral spikes 
•	Ability to trace origin (patient zero) 
•	Integrated containment mechanisms 
This project aims to simulate, detect, analyze, and contain misinformation spread in real time.
3. Methodology
The system combines network simulation + AI detection + graph analytics:
1.	Network Simulation 
o	Generates a realistic social graph 
o	Injects misinformation via a user (human/influencer) 
o	Simulates spread in phases: 
	Organic sharing 
	Bot amplification 
	Viral cascade 
2.	AI-Based Detection 
o	Uses LLM (LLaMA via Ollama) to compute: 
	Suspicion score (0–1) 
	Narrative category 
	Emotion 
3.	Graph Backtracking (Neo4j) 
o	Cypher queries identify the origin of spread 
o	Tracks propagation paths 
4.	Containment 
o	Deletes retweet edges 
o	Marks post as QUARANTINED 
o	Logs incident in MongoDB 
4. Results & Insights
•	Bot-driven amplification significantly increases spread velocity (>40% bot contribution in spikes) 
•	Viral spikes are detectable via retweet velocity thresholds 
•	AI achieves effective classification of suspicious content (score ≥ 0.5 triggers action)
Key Observations:
•	Influencers create faster initial spread 
•	Bots dominate mid-phase amplification 
•	Early detection reduces total propagation drastically 
5. Novelty
•	Hybrid Polyglot Architecture (Redis + MongoDB + Neo4j) 
•	Time-based propagation simulation (not static graphs) 
•	Real-time velocity-triggered AI detection 
•	Automated backtracking to patient zero using graph queries 
•	Integrated detect → trace → quarantine pipeline 
This reimagines misinformation defense as a live, adaptive system, not just a classifier.
