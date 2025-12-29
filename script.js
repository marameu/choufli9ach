(() => {
  document.documentElement.classList.add("js");

  window.addEventListener("load", () => {
    document.body.classList.add("is-ready");
  });

  const menuToggle = document.querySelector(".menu-toggle");
  const menuPanel = document.querySelector(".menu-panel");
  const menuOverlay = document.querySelector(".menu-overlay");
  const menuClose = document.querySelector(".menu-close");

  const setMenuState = (isOpen) => {
    document.body.classList.toggle("menu-open", isOpen);
    if (menuToggle) menuToggle.setAttribute("aria-expanded", String(isOpen));
    if (menuPanel) menuPanel.setAttribute("aria-hidden", String(!isOpen));
  };

  if (menuToggle) {
    menuToggle.setAttribute("aria-expanded", "false");
    menuToggle.addEventListener("click", () => {
      const isOpen = !document.body.classList.contains("menu-open");
      setMenuState(isOpen);
    });
  }

  if (menuClose) {
    menuClose.addEventListener("click", () => setMenuState(false));
  }

  if (menuOverlay) {
    menuOverlay.addEventListener("click", () => setMenuState(false));
  }

  if (menuPanel) {
    menuPanel.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => setMenuState(false));
    });
  }

  const lightbox = document.querySelector(".lightbox");
  const lightboxImage = document.querySelector(".lightbox-image");
  const lightboxClose = document.querySelector(".lightbox-close");
  const lightboxLinks = document.querySelectorAll(".product-image-link");

  const setLightboxState = (isOpen) => {
    if (!lightbox) return;
    lightbox.classList.toggle("is-open", isOpen);
    lightbox.setAttribute("aria-hidden", String(!isOpen));
  };

  if (lightboxLinks.length && lightbox && lightboxImage) {
    lightboxLinks.forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const href = link.getAttribute("href");
        const img = link.querySelector("img");
        if (href) lightboxImage.src = href;
        if (img) lightboxImage.alt = img.alt || "Produit";
        setLightboxState(true);
      });
    });
  }

  if (lightboxClose) {
    lightboxClose.addEventListener("click", () => setLightboxState(false));
  }

  if (lightbox) {
    lightbox.addEventListener("click", (event) => {
      if (event.target === lightbox) {
        setLightboxState(false);
      }
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setLightboxState(false);
    }
  });

  const initSlider = (gallery) => {
    const prevBtn = gallery.querySelector(".gallery-prev");
    const nextBtn = gallery.querySelector(".gallery-next");
    const slider = gallery.querySelector(".product-slider");
    const slides = slider ? Array.from(slider.children) : [];
    let index = 0;

    const goToIndex = (nextIndex) => {
      if (!slider || !slides.length) return;
      index = Math.max(0, Math.min(nextIndex, slides.length - 1));
      slider.style.transform = `translateX(-${index * 100}%)`;
    };

    goToIndex(0);

    if (prevBtn) {
      prevBtn.addEventListener("click", () => {
        goToIndex(index - 1);
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", () => {
        goToIndex(index + 1);
      });
    }
  };

  document.querySelectorAll(".product-gallery--slider").forEach((gallery) => {
    initSlider(gallery);
  });

  const promoInput = document.querySelector("#promoCode");
  const promoApply = document.querySelector("#promoApply");
  const promoNote = document.querySelector("#promoNote");
  const priceEl = document.querySelector(".product-price");
  const addCartBtn = document.querySelector(".btn-add-cart");

  if (promoInput && promoApply && priceEl && addCartBtn) {
    const basePrice = Number(priceEl.dataset.basePrice) || 0;
    const promoCode = "M&M";
    const promoKey = "promo_used";

    const setPrice = (value) => {
      priceEl.textContent = `${value} TND`;
      addCartBtn.dataset.price = String(value);
    };

    promoApply.addEventListener("click", () => {
      const entered = promoInput.value.trim();
      if (!entered) {
        if (promoNote) promoNote.textContent = "Entre un code promo.";
        return;
      }
      if (localStorage.getItem(promoKey) === "true") {
        if (promoNote) promoNote.textContent = "Code deja utilise.";
        return;
      }
      if (entered.toUpperCase() !== promoCode) {
        if (promoNote) promoNote.textContent = "Code promo invalide.";
        return;
      }
      const discounted = Math.round(basePrice * 0.9);
      setPrice(discounted);
      localStorage.setItem(promoKey, "true");
      if (promoNote) promoNote.textContent = "Promo appliquee: -10%.";
    });
  }

  const loadCart = () => {
    try {
      const raw = localStorage.getItem("choufli_cart");
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  };

  const cartItems = loadCart();
  const cartItemsContainer = document.querySelector("#cartItems");
  const cartTotal = document.querySelector("#cartTotal");
  const shippingFeeEl = document.querySelector("#shippingFee");
  const cartGrandTotal = document.querySelector("#cartGrandTotal");
  const cartCount = document.querySelector("#cartCount");
  const checkoutForm = document.querySelector("#checkoutForm");
  const checkoutButton = checkoutForm?.querySelector("button[type=\"submit\"]");

  const saveCart = () => {
    localStorage.setItem("choufli_cart", JSON.stringify(cartItems));
  };

  const updateCartCount = () => {
    if (cartCount) cartCount.textContent = String(cartItems.length);
  };

  const renderCart = () => {
    if (cartItemsContainer && cartTotal) {
      cartItemsContainer.innerHTML = "";

      if (cartItems.length === 0) {
        cartItemsContainer.innerHTML = "<p class=\"cart-empty\">Ton panier est vide pour le moment.</p>";
        cartTotal.textContent = "0 TND";
        if (shippingFeeEl) shippingFeeEl.textContent = "0 TND";
        if (cartGrandTotal) cartGrandTotal.textContent = "0 TND";
      } else {
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

        const shipping = 8;
        cartTotal.textContent = `${total} TND`;
        if (shippingFeeEl) shippingFeeEl.textContent = `${shipping} TND`;
        if (cartGrandTotal) cartGrandTotal.textContent = `${total + shipping} TND`;
      }
    }

    updateCartCount();
    if (checkoutButton) checkoutButton.disabled = cartItems.length === 0;
  };

  document.querySelectorAll(".btn-cart, .btn-add-cart").forEach((button) => {
    button.addEventListener("click", () => {
      const parent = button.closest(".product-info") || button.closest(".product-card") || document;
      const sizeSelect = parent.querySelector(".product-size");
      const size = sizeSelect ? sizeSelect.value : "S";
      const name = button.dataset.product;
      const price = Number(button.dataset.price) || 0;
      cartItems.push({ name, price, size });
      saveCart();
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
          saveCart();
        }
      }
    });

    cartItemsContainer.addEventListener("click", (event) => {
      const target = event.target;
      if (target instanceof HTMLElement && target.dataset.remove) {
        const index = Number(target.dataset.remove);
        cartItems.splice(index, 1);
        saveCart();
        renderCart();
      }
    });
  }

  const orderEndpoints = [
    {
      url: "https://choufli9ach.onrender.com/api/orders",
      mode: "cors",
      allowOpaque: false,
    },
    {
      url: "https://script.google.com/macros/s/AKfycbxssDv9ayTHWt2paeP6fBkpxVQnal6MBbbUbbAijqhCSuq6pMOtKEUIndmz-ZjmJ5if/exec",
      mode: "no-cors",
      allowOpaque: true,
    },
  ];

  const sendOrder = async (payload) => {
    const results = await Promise.allSettled(
      orderEndpoints.map(async (endpoint) => {
        const response = await fetch(endpoint.url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          mode: endpoint.mode,
        });
        if (endpoint.allowOpaque && response.type === "opaque") {
          return response;
        }
        if (!response.ok) {
          throw new Error(`Order failed: ${endpoint.url}`);
        }
        return response;
      })
    );
    const successCount = results.filter((item) => item.status === "fulfilled").length;
    if (successCount === 0) {
      throw new Error("Order failed");
    }
    return successCount;
  };

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
        total: cartItems.reduce((sum, item) => sum + item.price, 0) + (cartItems.length ? 8 : 0),
      };

      if (checkoutButton) checkoutButton.disabled = true;
      try {
        const successCount = await sendOrder(payload);
        if (successCount < orderEndpoints.length) {
          alert("Commande enregistree, mais une copie n'a pas pu etre envoyee.");
        } else {
          alert("Merci ! Votre commande est enregistree. Paiement a la livraison.");
        }
        checkoutForm.reset();
        cartItems.length = 0;
        saveCart();
        renderCart();
      } catch (error) {
        alert("Impossible d'envoyer la commande. Reessaie dans quelques instants.");
        renderCart();
      }
    });
  }

  renderCart();
})();
