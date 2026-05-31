from groq import Groq
from ddgs import DDGS
from newspaper import Article
import json
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# ===== 1. MODÈLE =====
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ===== 2. TOOLS =====

def search_web(query: str, max_results: int = 5):
    """Cherche sur le web avec DuckDuckGo"""
    print(f"🔍 Recherche: {query}")
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r["title"],
                "url": r["href"],
                "snippet": r["body"]
            })
    return results

def scrape_article(url: str):
    """Lit le contenu complet d'une page web"""
    print(f"📄 Lecture: {url}")
    try:
        article = Article(url)
        article.download()
        article.parse()
        return {
            "title": article.title,
            "text": article.text[:3000],  # max 3000 caractères
            "url": url
        }
    except:
        return {"error": f"Impossible de lire {url}"}

def summarize(text: str, topic: str):
    """Résume un texte avec Llama"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""Résume ce texte sur le sujet '{topic}' en français.
Garde les points clés, chiffres importants et conclusions.
Maximum 200 mots.

Texte: {text}"""
        }]
    )
    return response.choices[0].message.content

def save_report(topic: str, results: list):
    """Sauvegarde le rapport en fichier markdown"""
    filename = f"rapport_{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Rapport de Recherche: {topic}\n\n")
        f.write(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
        for i, r in enumerate(results, 1):
            f.write(f"## Source {i}: {r['title']}\n")
            f.write(f"*URL:* {r['url']}\n\n")
            f.write(f"{r['summary']}\n\n")
            f.write("---\n\n")
    return filename

# ===== 3. AGENT PRINCIPAL =====

def research_agent(topic: str):
    print(f"\n{'='*50}")
    print(f"🤖 Recherche sur: {topic}")
    print(f"{'='*50}\n")

    # Étape 1 — Chercher sur le web
    search_results = search_web(topic, max_results=4)
    print(f"✅ {len(search_results)} résultats trouvés\n")

    # Étape 2 — Lire et résumer chaque article
    detailed_results = []
    for result in search_results:
        print(f"\n📰 {result['title']}")

        # Scraper l'article
        article = scrape_article(result["url"])

        if "error" not in article:
            # Résumer
            summary = summarize(article["text"], topic)
            detailed_results.append({
                "title": result["title"],
                "url": result["url"],
                "summary": summary
            })
            print(f"✅ Résumé créé")
        else:
            # Utiliser le snippet si scraping échoue
            detailed_results.append({
                "title": result["title"],
                "url": result["url"],
                "summary": result["snippet"]
            })
            print(f"⚠️ Utilisé snippet")

    # Étape 3 — Synthèse finale
    print(f"\n{'='*50}")
    print("📊 SYNTHÈSE FINALE")
    print(f"{'='*50}\n")

    all_summaries = "\n\n".join([
        f"Source: {r['title']}\n{r['summary']}"
        for r in detailed_results
    ])

    synthesis = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""Tu es un expert en recherche et analyse.
Fais une synthèse complète sur '{topic}' basée sur ces sources.

Structure ta réponse ainsi:
1. 📌 Points clés
2. 📈 Tendances actuelles
3. 💡 Conclusions

Sources:
{all_summaries}"""
        }]
    )

    print(synthesis.choices[0].message.content)

    # Étape 4 — Sauvegarder le rapport
    filename = save_report(topic, detailed_results)
    print(f"\n💾 Rapport sauvegardé: {filename}")

    return detailed_results

# ===== 4. INTERFACE =====
print("🔍 Agent de Recherche Web")
print("Tapez 'quit' pour quitter\n")

while True:
    topic = input("🔎 Sujet à rechercher: ")
    if topic.lower() == "quit":
        break
    if topic.strip():
        research_agent(topic)