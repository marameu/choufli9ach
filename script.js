(() => {
  document.documentElement.classList.add("js");

  window.addEventListener("load", () => {
    document.body.classList.add("is-ready");
  });

  const cartItems = [];
  const cartItemsContainer = document.querySelector("#cartItems");
  const cartTotal = document.querySelector("#cartTotal");
  const cartCount = document.querySelector("#cartCount");
  const checkoutForm = document.querySelector("#checkoutForm");
  const checkoutButton = checkoutForm?.querySelector("button[type=\"submit\"]");

  const renderCart = () => {
    if (!cartItemsContainer || !cartTotal) return;
    cartItemsContainer.innerHTML = "";

    if (cartItems.length === 0) {
      cartItemsContainer.innerHTML = "<p class=\"cart-empty\">Ton panier est vide pour le moment.</p>";
      cartTotal.textContent = "0 TND";
      if (cartCount) cartCount.textContent = "0";
      if (checkoutButton) checkoutButton.disabled = true;
      return;
    }

    let total = 0;
    cartItems.forEach((item, index) => {
      total += item.price;
      const itemEl = document.createElement("div");
      itemEl.className = "cart-item";
      itemEl.innerHTML = `
        <h4>${item.name}</h4>
        <div class="cart-controls">
          <select data-index="${index}" class="cart-size">
            <option value="S" ${item.size === "S" ? "selected" : ""}>S</option>
            <option value="M" ${item.size === "M" ? "selected" : ""}>M</option>
            <option value="L" ${item.size === "L" ? "selected" : ""}>L</option>
            <option value="XL" ${item.size === "XL" ? "selected" : ""}>XL</option>
          </select>
          <span>${item.price} TND</span>
          <button type="button" data-remove="${index}">Retirer</button>
        </div>
      `;
      cartItemsContainer.appendChild(itemEl);
    });

    cartTotal.textContent = `${total} TND`;
    if (cartCount) cartCount.textContent = String(cartItems.length);
    if (checkoutButton) checkoutButton.disabled = false;
  };

  document.querySelectorAll(".btn-cart").forEach((button) => {
    button.addEventListener("click", () => {
      const name = button.dataset.product;
      const price = Number(button.dataset.price) || 0;
      cartItems.push({ name, price, size: "S" });
      renderCart();
      document.querySelector("#panier")?.scrollIntoView({ behavior: "smooth" });
    });
  });

  if (cartItemsContainer) {
    cartItemsContainer.addEventListener("change", (event) => {
      const target = event.target;
      if (target.classList.contains("cart-size")) {
        const index = Number(target.dataset.index);
        if (!Number.isNaN(index) && cartItems[index]) {
          cartItems[index].size = target.value;
        }
      }
    });

    cartItemsContainer.addEventListener("click", (event) => {
      const target = event.target;
      if (target instanceof HTMLElement && target.dataset.remove) {
        const index = Number(target.dataset.remove);
        cartItems.splice(index, 1);
        renderCart();
      }
    });
  }

  if (checkoutForm) {
    checkoutForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (cartItems.length === 0) {
        alert("Ajoute un produit au panier avant de confirmer.");
        return;
      }
      const formData = new FormData(checkoutForm);
      const payload = {
        customer: {
          name: String(formData.get("name") || "").trim(),
          phone: String(formData.get("phone") || "").trim(),
          address: String(formData.get("address") || "").trim(),
        },
        items: cartItems,
        total: cartItems.reduce((sum, item) => sum + item.price, 0),
      };

      if (checkoutButton) checkoutButton.disabled = true;
      try {
        const response = await fetch("/api/orders", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          throw new Error("Order failed");
        }

        alert("Merci ! Votre commande est enregistree. Paiement a la livraison.");
        checkoutForm.reset();
        cartItems.length = 0;
        renderCart();
      } catch (error) {
        alert("Impossible d'envoyer la commande. Reessaie dans quelques instants.");
        renderCart();
      }
    });
  }

  renderCart();
})();
