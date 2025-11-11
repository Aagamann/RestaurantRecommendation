let ratingChart = null;
let sentimentChart = null;

async function fetchRestaurants() {
  const res = await fetch("/api/restaurants");
  const names = await res.json();
  const dl = document.querySelector("#restaurants");
  dl.innerHTML = "";
  names.forEach(n => {
    const opt = document.createElement("option");
    opt.value = n;
    dl.appendChild(opt);
  });
}

function ensureChart(ctx, type, data, options = {}) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  if (ctx.id === "ratingChart" && ratingChart) { ratingChart.destroy(); ratingChart = null; }
  if (ctx.id === "sentimentChart" && sentimentChart) { sentimentChart.destroy(); sentimentChart = null; }

  const chart = new Chart(ctx, { type, data, options });
  if (ctx.id === "ratingChart") ratingChart = chart;
  if (ctx.id === "sentimentChart") sentimentChart = chart;
}

async function search() {
  const input = document.querySelector("#restaurant");
  const status = document.querySelector("#status");
  const name = input.value.trim();
  if (!name) return;

  document.querySelector("#reviewsList").innerHTML = "";
  status.textContent = "Loading…";

  try {
    const res = await fetch(`/api/summary?restaurant=${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error("Not found");
    const data = await res.json();

    document.querySelector("#resName").textContent = data.restaurant;
    document.querySelector("#resLoc").textContent = data.location || "—";
    document.querySelector("#resContact").textContent = data.contact || "—";

    const imgEl = document.querySelector("#resImg");
    const imgFile = data.restaurant.replace(/\s+/g, '').toLowerCase() + ".jpg";
    imgEl.src = `/static/images/${imgFile}`;
    imgEl.onerror = () => { imgEl.src = "/static/images/default.jpg"; };

    document.querySelector("#totalReviews").textContent = data.total_reviews;
    document.querySelector("#avgRating").textContent = data.average_rating;
    document.querySelector("#posCount").textContent = data.positive;
    document.querySelector("#negCount").textContent = data.negative;

    const labels = ["1","2","3","4","5"];
    const values = labels.map(k => data.rating_counts[k] || 0);
    ensureChart(
      document.getElementById("ratingChart").getContext("2d"),
      "bar",
      { labels, datasets: [{ label:"Count", data: values, backgroundColor:"rgba(54,162,235,0.6)", borderColor:"rgba(54,162,235,1)", borderWidth:1 }] },
      { responsive:true, plugins:{ legend:{ display:false } }, scales:{ y:{ beginAtZero:true, precision:0 } } }
    );

    ensureChart(
      document.getElementById("sentimentChart").getContext("2d"),
      "doughnut",
      { labels:["Positive","Negative"], datasets:[{ data:[data.positive,data.negative], backgroundColor:["rgba(75,192,192,0.7)","rgba(255,99,132,0.7)"], borderColor:["rgba(75,192,192,1)","rgba(255,99,132,1)"], borderWidth:1 }] },
      { responsive:true, plugins:{ legend:{ position:"bottom" } } }
    );

    const reviewsList = document.querySelector("#reviewsList");
    (data.examples.positive || []).forEach(t => {
      const li = document.createElement("li");
      li.textContent = t;
      reviewsList.appendChild(li);
    });
    (data.examples.negative || []).forEach(t => {
      const li = document.createElement("li");
      li.textContent = t;
      reviewsList.appendChild(li);
    });

    status.textContent = "Done";

    // 🔄 Load similar restaurants (CBF)
    fetchSimilarRestaurants(data.restaurant);

  } catch(e) {
    status.textContent = "Not found";
    document.querySelector("#resName").textContent = "—";
    document.querySelector("#resLoc").textContent = "—";
    document.querySelector("#resContact").textContent = "—";
    document.querySelector("#totalReviews").textContent = "0";
    document.querySelector("#avgRating").textContent = "0.0";
    document.querySelector("#posCount").textContent = "0";
    document.querySelector("#negCount").textContent = "0";
    document.querySelector("#reviewsList").innerHTML = "";
    if (ratingChart){ ratingChart.destroy(); ratingChart=null; }
    if (sentimentChart){ sentimentChart.destroy(); sentimentChart=null; }
  }
}

async function submitFeedback() {
  const reviewText = document.querySelector("#newReview").value.trim();
  const ratingValue = document.querySelector("#ratingSelect").value;
  const restaurant = document.querySelector("#resName").textContent;
  const statusEl = document.querySelector("#feedbackStatus");
  const sentimentEl = document.querySelector("#predictedSentiment");

  if (!reviewText && !ratingValue) {
    statusEl.textContent = "Please enter a review or select a rating!";
    sentimentEl.textContent = "";
    return;
  }

  statusEl.textContent = "Submitting...";
  sentimentEl.textContent = "";

  try {
    const payload = { restaurant };
    if (reviewText) payload.review = reviewText;
    if (ratingValue) payload.rating = parseInt(ratingValue);

    const res = await fetch("/api/submit_feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!res.ok && data.error) {
      statusEl.textContent = data.error;
    } else {
      statusEl.textContent = "Feedback submitted!";
      sentimentEl.textContent = data.sentiment ? `Saved as ${data.sentiment}` : "";
      document.querySelector("#newReview").value = "";
      document.querySelector("#ratingSelect").value = "";

      await search(); // Refresh dashboard
      fetchRecommendationsForUser(restaurant, data.sentiment);
    }
  } catch (e) {
    statusEl.textContent = "Error submitting feedback";
  }
}

async function fetchRecommendationsForUser(restaurant, sentiment) {
  try {
    const res = await fetch(`/api/user_recommendations?restaurant=${encodeURIComponent(restaurant)}&sentiment=${sentiment}`);
    const data = await res.json();

    const container = document.querySelector("#userRecommendations");
    container.innerHTML = "<h3>🍴 Recommended for You</h3>";

    if (!data.length) {
      container.innerHTML += "<p>No recommendations available.</p>";
      return;
    }

    data.forEach(r => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <h4>${r.restaurant}</h4>
        <p><strong>Location:</strong> ${r.location || "N/A"}</p>
        <p><strong>Contact:</strong> ${r.contact || "N/A"}</p>
        <p><strong>Avg Rating:</strong> ${r.average_rating || "0.0"}</p>
      `;
      card.addEventListener("click", () => {
        window.location.href = `/dashboard?restaurant=${encodeURIComponent(r.restaurant)}`;
      });
      container.appendChild(card);
    });
  } catch (e) {
    console.error("Error fetching recommendations:", e);
  }
}

async function fetchSimilarRestaurants(restaurant) {
  try {
    const res = await fetch(`/api/similar_restaurants?restaurant=${encodeURIComponent(restaurant)}`);
    const data = await res.json();

    const container = document.querySelector("#similarRestaurants");
    container.innerHTML = "<h3>🔍 Similar Restaurants</h3>";

    if (!data.length) {
      container.innerHTML += "<p>No similar restaurants found.</p>";
      return;
    }

    data.forEach(r => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <h4>${r.restaurant}</h4>
        <p><strong>Location:</strong> ${r.location || "N/A"}</p>
        <p><strong>Contact:</strong> ${r.contact || "N/A"}</p>
      `;
      card.addEventListener("click", () => {
        window.location.href = `/dashboard?restaurant=${encodeURIComponent(r.restaurant)}`;
      });
      container.appendChild(card);
    });
  } catch (e) {
    console.error("Error fetching similar restaurants:", e);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await fetchRestaurants();
  document.querySelector("#searchBtn").addEventListener("click", search);
  document.querySelector("#restaurant").addEventListener("keydown", (e)=>{ if(e.key==="Enter") search(); });
  document.querySelector("#submitFeedbackBtn").addEventListener("click", submitFeedback);

  const params = new URLSearchParams(window.location.search);
  const restaurant = params.get("restaurant");
  if (restaurant) {
    document.querySelector("#restaurant").value = restaurant;
    search();
  }
});
