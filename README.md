AI-Powered Misinformation Detection & Containment System
Overview

The AI-Powered Misinformation Detection & Containment System is a real-time simulation platform designed to identify, analyze, and mitigate the spread of misinformation across social networks. The system combines Large Language Models (LLMs), graph analytics, and a polyglot database architecture to detect suspicious content, trace its origin, and automatically contain its propagation.

Unlike traditional misinformation classifiers, this project models the complete lifecycle of information spread—from the initial post to viral amplification—while providing automated containment mechanisms.

Dataset

The project utilizes a synthetic, dynamically generated dataset that simulates realistic social media interactions.

Data is distributed across a polyglot architecture to leverage the strengths of different database technologies:

Neo4j (Graph Database)
Models relationships between users and posts.
Nodes: Users, Posts
Relationships:
FOLLOWS
POSTED
RETWEETED
MongoDB
Stores historical misinformation incidents.
Maintains quarantine records.
Preserves threat logs for future analysis.
Redis
Caches AI inference results.
Eliminates redundant LLM computations.
Improves overall system performance.
Dataset Features

The simulated network includes:

Multiple user types:
Human
Bot
Influencer
Time-based retweet propagation
Content metadata including:
Post text
Narrative category
Emotional tone
Suspicion score
Data Preprocessing

Before analysis, the system performs several preprocessing steps:

Text normalization for consistent LLM inference
Graph construction for propagation analysis
Redis-based caching to reduce repeated AI processing
Problem Statement

Social media platforms enable misinformation to spread rapidly, particularly when amplified by automated bots and influential accounts.

Most existing approaches primarily focus on content classification but fail to provide:

Real-time detection of viral misinformation
Identification of the original source ("Patient Zero")
Automated containment of malicious content

This project addresses these challenges by combining AI-powered content analysis with graph-based propagation tracking to detect, trace, and contain misinformation in real time.

Methodology

The system consists of four major components.

1. Social Network Simulation

A realistic social media network is generated using graph structures.

The simulation includes:

Human users
Bot accounts
Influencers

Misinformation is introduced into the network and propagates through three distinct phases:

Organic user sharing
Bot-driven amplification
Viral cascade through influencers
2. AI-Based Content Detection

Each post is analyzed using LLaMA running locally via Ollama.

The model predicts:

Suspicion Score (0–1)
Narrative Category
Emotional Tone

Posts with a suspicion score greater than or equal to 0.5 are flagged for further investigation.

3. Graph-Based Backtracking

Neo4j graph analytics are used to reconstruct the propagation path.

Using Cypher queries, the system can:

Identify the original source (Patient Zero)
Trace retweet chains
Analyze propagation paths
Measure spread velocity
4. Automated Containment

Once misinformation is confirmed, the system automatically performs containment actions.

These include:

Removing retweet relationships
Marking the post as QUARANTINED
Logging the incident into MongoDB

This enables rapid mitigation while maintaining a historical threat repository.

Results

The simulation demonstrates several important observations:

Bot activity contributes more than 40% of viral misinformation spikes.
Retweet velocity effectively identifies viral outbreaks in real time.
AI-generated suspicion scores successfully classify suspicious content for automated intervention.
Key Insights
Influencers accelerate the initial spread of misinformation.
Bots dominate the amplification phase.
Early detection significantly reduces overall network propagation.
Combining AI with graph analytics provides greater visibility into misinformation spread than standalone classifiers.
Key Features
Real-time misinformation detection
AI-powered narrative and emotion analysis
Patient Zero identification using graph traversal
Temporal propagation simulation
Automated content quarantine
Multi-database (Polyglot) architecture
Redis-based AI result caching
End-to-end Detect → Trace → Quarantine pipeline
Novelty

This project introduces several unique contributions:

Hybrid Polyglot Database Architecture integrating Neo4j, MongoDB, and Redis.
Time-aware misinformation propagation simulation instead of static graph analysis.
Velocity-triggered AI detection using LLaMA.
Automated identification of the original misinformation source through graph backtracking.
Fully integrated real-time Detect → Trace → Quarantine workflow.
