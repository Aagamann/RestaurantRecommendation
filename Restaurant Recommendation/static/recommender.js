async function loadRestaurants() {
  const res = await fetch("/api/restaurants_with_details");
  const data = await res.json();
  const grid = document.querySelector("#restaurantGrid");
  grid.innerHTML = "";

  data.forEach(r => {
    const card = createRestaurantCard(r, { showRating: false });
    grid.appendChild(card);
  });
}

async function loadRecommendations() {
  try {
    const res = await fetch("/api/recommendations");
    const data = await res.json();
    const grid = document.querySelector("#recommendGrid");
    grid.innerHTML = "";

    data.sort((a, b) => (b.average_rating || 0) - (a.average_rating || 0));
    data.forEach(r => {
      const card = createRestaurantCard(r, { showRating: false });
      grid.appendChild(card);
    });
  } catch (e) {
    console.error("Error loading recommendations:", e);
  }
}

async function loadLocationRecommendations(location, gridId) {
  try {
    const res = await fetch(`/api/recommend_by_location?location=${encodeURIComponent(location)}`);
    const data = await res.json();
    const grid = document.querySelector(gridId);
    grid.innerHTML = "";

    data.sort((a, b) => (b.average_rating || 0) - (a.average_rating || 0));
    data.forEach(r => {
      const card = createRestaurantCard(r, { showRating: true });
      grid.appendChild(card);
    });
  } catch (e) {
    console.error(`Error loading recommendations for ${location}:`, e);
  }
}

// 🧠 Load similar restaurants dynamically
async function loadSimilarRestaurants(restaurantName) {
  if (!restaurantName) return;
  const heading = document.querySelector("#selectedRestaurant");
  const grid = document.querySelector("#similarGrid");
  heading.textContent = `Similar to "${restaurantName}"`;
  grid.innerHTML = "<p>Loading similar restaurants...</p>";

  try {
    const res = await fetch(`/api/similar_restaurants?restaurant=${encodeURIComponent(restaurantName)}`);
    const data = await res.json();
    grid.innerHTML = "";

    if (!data.length) {
      grid.innerHTML = "<p>No similar restaurants found.</p>";
      return;
    }

    data.forEach(r => {
      const card = createRestaurantCard(r, { showRating: false });
      grid.appendChild(card);
    });

    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (e) {
    console.error("Error loading similar restaurants:", e);
    grid.innerHTML = "<p>Error loading recommendations.</p>";
  }
}

// 🎨 Card creation logic
function createRestaurantCard(r, options = { showRating: true }) {
  const card = document.createElement("div");
  card.className = "card";

  const img = document.createElement("img");
  img.src = `/static/images/${r.restaurant.replace(/\s+/g, '').toLowerCase()}.jpg`;
  img.alt = r.restaurant;
  img.style = "width:100%; border-radius:8px; margin-bottom:0.5rem;";
  img.onerror = () => img.src = "/static/images/default.jpg";
  card.appendChild(img);

  const info = document.createElement("div");
  info.innerHTML = `
    <h3>${r.restaurant}</h3>
    <p><strong>Location:</strong> ${r.location || "Not available"}</p>
    <p><strong>Contact:</strong> ${r.contact || "Not available"}</p>
    ${options.showRating && r.average_rating !== undefined 
        ? `<p><strong>Avg Rating:</strong> ${r.average_rating || "0.0"}</p>` 
        : ""}
  `;
  card.appendChild(info);

  // ✨ Dual click behavior
  let clickTimeout = null;
  card.addEventListener("click", () => {
    if (clickTimeout) {
      // Double click → open dashboard
      clearTimeout(clickTimeout);
      clickTimeout = null;
      window.location.href = `/dashboard?restaurant=${encodeURIComponent(r.restaurant)}`;
    } else {
      // Single click → show similar restaurants
      clickTimeout = setTimeout(() => {
        loadSimilarRestaurants(r.restaurant);
        clickTimeout = null;
      }, 250); // short delay to distinguish between single & double click
    }
  });

  return card;
}

document.addEventListener("DOMContentLoaded", () => {
  loadRestaurants();
  loadRecommendations();
  loadLocationRecommendations("Thamel", "#thamelGrid");
  loadLocationRecommendations("Kathmandu", "#kathmanduGrid");
  loadLocationRecommendations("Bhaktapur", "#bhaktapurGrid");
  loadLocationRecommendations("Lalitpur", "#lalitpurGrid");
});
