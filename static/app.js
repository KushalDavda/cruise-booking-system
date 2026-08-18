/**
 * Odysseus Cruise Booking System - Client Application JavaScript
 */

const state = {
    cruises: [],
    selectedCruise: null,
    role: 'Customer',
    currentBreakdown: null,
    lastBookingRef: null
};

// Initialize Application on Page Load
document.addEventListener('DOMContentLoaded', () => {
    fetchCruises();
    fetchAdminRules();
});

// --- Role Switcher ---
function handleRoleChange() {
    state.role = document.getElementById('roleSelect').value;
    const adminBtn = document.getElementById('tabAdminBtn');
    if (state.role === 'Admin') {
        adminBtn.style.display = 'block';
    } else {
        adminBtn.style.display = 'none';
        if (document.getElementById('viewAdmin').classList.contains('active')) {
            switchTab('catalog');
        }
    }
}

// --- Navigation Tabs ---
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));

    if (tabName === 'catalog') {
        document.getElementById('tabCatalogBtn').classList.add('active');
        document.getElementById('viewCatalog').classList.add('active');
    } else if (tabName === 'booking') {
        document.getElementById('tabBookingBtn').classList.add('active');
        document.getElementById('viewBooking').classList.add('active');
    } else if (tabName === 'lookup') {
        document.getElementById('tabLookupBtn').classList.add('active');
        document.getElementById('viewLookup').classList.add('active');
    } else if (tabName === 'admin') {
        document.getElementById('tabAdminBtn').classList.add('active');
        document.getElementById('viewAdmin').classList.add('active');
    }
}

// --- Catalog API & Render ---
async function fetchCruises() {
    try {
        const response = await fetch('/api/cruises');
        const data = await response.json();
        state.cruises = data.cruises || [];
        renderCruises();
    } catch (err) {
        console.error('Error fetching cruises:', err);
    }
}

function renderCruises() {
    const grid = document.getElementById('cruisesGrid');
    const search = document.getElementById('searchInput').value.toLowerCase().strip ? document.getElementById('searchInput').value.toLowerCase().strip() : document.getElementById('searchInput').value.toLowerCase();

    const filtered = state.cruises.filter(c => 
        c.ship_name.toLowerCase().includes(search) ||
        c.cruise_line.toLowerCase().includes(search) ||
        c.destination.toLowerCase().includes(search)
    );

    if (filtered.length === 0) {
        grid.innerHTML = `<div class="placeholder-text" style="grid-column: 1/-1;">No cruises found matching your query.</div>`;
        return;
    }

    grid.innerHTML = filtered.map(c => {
        let capClass = 'available';
        let capText = `${c.capacity_left} Left`;
        let isSoldOut = false;

        if (c.capacity_left <= 0) {
            capClass = 'soldout';
            capText = 'Sold Out';
            isSoldOut = true;
        } else if (c.capacity_left <= 4) {
            capClass = 'low';
            capText = `Only ${c.capacity_left} Left!`;
        }

        return `
            <div class="cruise-card">
                <div>
                    <div class="card-top">
                        <span class="cruise-line">${c.cruise_line}</span>
                        <span class="capacity-badge ${capClass}">${capText}</span>
                    </div>
                    <h3 class="ship-name">${c.ship_name}</h3>
                    <p class="destination">🚩 <strong>Departs From:</strong> ${c.departure_port || 'PortMiami, FL'}</p>
                    <p class="destination">📍 <strong>Destination:</strong> ${c.destination} • 🌙 ${c.nights} Nights</p>
                </div>
                <div class="card-bottom">
                    <div class="price-tag">
                        <span class="amount">$${c.adult_fare.toLocaleString()}</span>
                        <span class="unit">per adult</span>
                    </div>
                    <button class="btn-primary" ${isSoldOut ? 'disabled' : ''} onclick="selectCruise(${c.id})">
                        ${isSoldOut ? 'Sold Out' : 'Select & Book'}
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// --- Select Cruise & Form Sync ---
function selectCruise(cruiseId) {
    const cruise = state.cruises.find(c => c.id === cruiseId);
    if (!cruise) return;

    state.selectedCruise = cruise;
    renderSelectedCruiseBanner();
    switchTab('booking');
    triggerPriceRecalc();
}

function renderSelectedCruiseBanner() {
    const banner = document.getElementById('selectedCruiseBanner');
    if (!state.selectedCruise) {
        banner.innerHTML = `<p class="placeholder-text">Please select a cruise from the Catalog tab first.</p>`;
        return;
    }

    const c = state.selectedCruise;
    banner.innerHTML = `
        <h3>${c.ship_name} (${c.cruise_line})</h3>
        <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">
            🚩 <strong>Departure Port (Source):</strong> ${c.departure_port || 'PortMiami, FL'}<br>
            📍 <strong>Destination:</strong> ${c.destination} • 🌙 ${c.nights} Nights • Base Adult Fare: <strong>$${c.adult_fare.toLocaleString()}</strong> • Capacity Left: <strong>${c.capacity_left}</strong>
        </p>
    `;
}

// --- Passenger Dynamic Inputs ---
function handlePaxChange() {
    const childCount = parseInt(document.getElementById('childCount').value) || 0;
    const container = document.getElementById('childAgesContainer');
    const inputsDiv = document.getElementById('childAgesInputs');

    if (childCount > 0) {
        container.style.display = 'block';
        let html = '';
        for (let i = 0; i < childCount; i++) {
            html += `
                <div>
                    <label style="font-size: 12px;">Child ${i+1} Age:</label>
                    <input type="number" class="child-age-input" min="0" max="17" value="6" onchange="triggerPriceRecalc()" required>
                </div>
            `;
        }
        inputsDiv.innerHTML = html;
    } else {
        container.style.display = 'none';
        inputsDiv.innerHTML = '';
    }

    triggerPriceRecalc();
}

// --- Real-time Price Recalculation ---
async function triggerPriceRecalc() {
    if (!state.selectedCruise) {
        document.getElementById('pricingBreakdownContainer').innerHTML = `<p class="placeholder-text">Select a cruise to view live pricing calculation.</p>`;
        return;
    }

    const adultCount = parseInt(document.getElementById('adultCount').value) || 1;
    const childAgeInputs = document.querySelectorAll('.child-age-input');
    const childAges = Array.from(childAgeInputs).map(inp => parseInt(inp.value) || 0);
    const totalPax = adultCount + childAges.length;

    const promoCode = document.getElementById('promoCodeInput').value.trim();
    const customerEmail = document.getElementById('custEmail').value.trim();

    const selectedServices = [];
    if (document.getElementById('svcInsurance').checked) selectedServices.push('INSURANCE');
    if (document.getElementById('svcWifi').checked) selectedServices.push('WIFI');
    if (document.getElementById('svcExcursion').checked) selectedServices.push('EXCURSION');

    const submitBtn = document.getElementById('submitBookingBtn');
    if (totalPax > 6) {
        document.getElementById('pricingBreakdownContainer').innerHTML = `<div class="promo-feedback error" style="font-size: 15px;">❌ Maximum 6 passengers allowed per booking (Current: ${totalPax}).</div>`;
        submitBtn.disabled = true;
        return;
    }
    submitBtn.disabled = false;

    const payload = {
        cruise_id: state.selectedCruise.id,
        adult_count: adultCount,
        child_ages: childAges,
        services_selected: selectedServices,
        promo_code: promoCode || null,
        customer_email: customerEmail || null
    };

    try {
        const response = await fetch('/api/pricing/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errData = await response.json();
            document.getElementById('pricingBreakdownContainer').innerHTML = `<div class="promo-feedback error">❌ ${errData.detail}</div>`;
            return;
        }

        const data = await response.json();
        state.currentBreakdown = data;
        renderPriceBreakdown(data);
    } catch (err) {
        console.error('Calculation error:', err);
    }
}

function renderPriceBreakdown(data) {
    const ps = data.pricing_summary;
    const container = document.getElementById('pricingBreakdownContainer');
    const promoFeedback = document.getElementById('promoFeedback');

    // Handle Promo feedback banner
    if (ps.promo_code.applied_code) {
        promoFeedback.className = 'promo-feedback success';
        promoFeedback.innerHTML = `✅ Promo Code '${ps.promo_code.applied_code}' applied! Savings: -$${ps.promo_code.discount_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    } else if (ps.promo_code.error_message) {
        promoFeedback.className = 'promo-feedback error';
        promoFeedback.innerHTML = `❌ ${ps.promo_code.error_message}`;
    } else {
        promoFeedback.className = 'promo-feedback';
        promoFeedback.innerHTML = '';
    }

    let servicesHtml = '';
    if (ps.services && ps.services.length > 0) {
        servicesHtml = ps.services.map(s => `
            <div class="breakdown-row">
                <span>${s.name} (${s.detail})</span>
                <span>+$${s.total_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>
        `).join('');
    }

    container.innerHTML = `
        <div class="price-breakdown-list">
            <div class="breakdown-row">
                <span>Adult Fares (${data.passengers_summary.adult_count} x $${data.cruise.adult_base_fare.toLocaleString()})</span>
                <span>$${ps.adult_subtotal.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>
            
            ${data.passengers_summary.child_count > 0 ? `
                <div class="breakdown-row">
                    <span>Child Fares (${data.passengers_summary.child_count} children)</span>
                    <span>+$${ps.child_subtotal.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                </div>
            ` : ''}

            <div class="breakdown-row subtotal">
                <span>Gross Cruise Fare</span>
                <span>$${ps.gross_cruise_subtotal.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>

            ${ps.group_discount.percentage > 0 ? `
                <div class="breakdown-row discount-text">
                    <span>Group Discount (${ps.group_discount.percentage}% off Cruise Fare)</span>
                    <span>-$${ps.group_discount.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                </div>
            ` : ''}

            ${servicesHtml}

            <div class="breakdown-row subtotal">
                <span>Pre-tax Subtotal</span>
                <span>$${ps.pre_promo_subtotal.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>

            ${ps.promo_code.discount_amount > 0 ? `
                <div class="breakdown-row discount-text">
                    <span>Promotional Code (${ps.promo_code.applied_code})</span>
                    <span>-$${ps.promo_code.discount_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                </div>
            ` : ''}

            <div class="breakdown-row">
                <span>Estimated Tax (${ps.tax.percentage_label})</span>
                <span>+$${ps.tax.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>

            <div class="breakdown-row total">
                <span>Final Total Charged</span>
                <span>$${ps.total_price.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>
        </div>
    `;
}

// --- Booking Submission ---
async function handleBookingSubmit(event) {
    event.preventDefault();
    if (!state.selectedCruise) {
        alert('Please select a cruise itinerary first.');
        return;
    }

    const name = document.getElementById('custName').value.trim();
    const email = document.getElementById('custEmail').value.trim();
    const adultCount = parseInt(document.getElementById('adultCount').value) || 1;
    const childAgeInputs = document.querySelectorAll('.child-age-input');
    const childAges = Array.from(childAgeInputs).map(inp => parseInt(inp.value) || 0);

    const promoCode = document.getElementById('promoCodeInput').value.trim();
    const selectedServices = [];
    if (document.getElementById('svcInsurance').checked) selectedServices.push('INSURANCE');
    if (document.getElementById('svcWifi').checked) selectedServices.push('WIFI');
    if (document.getElementById('svcExcursion').checked) selectedServices.push('EXCURSION');

    const payload = {
        cruise_id: state.selectedCruise.id,
        customer_name: name,
        customer_email: email,
        adult_count: adultCount,
        child_ages: childAges,
        services_selected: selectedServices,
        promo_code: promoCode || null
    };

    try {
        const response = await fetch('/api/bookings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            alert(`Booking Rejected: ${data.detail}`);
            return;
        }

        state.lastBookingRef = data.booking_reference;
        document.getElementById('modalRefCode').innerText = data.booking_reference;
        const totalPaxCount = data.passengers_summary ? data.passengers_summary.total_passengers : (adultCount + childAges.length);
        document.getElementById('modalSummaryDetails').innerHTML = `
            <p style="margin-top: 10px; color: var(--text-muted);">
                Customer: <strong>${name}</strong> (${email})<br>
                Ship: <strong>${state.selectedCruise.ship_name}</strong><br>
                Total Passengers: <strong>${totalPaxCount}</strong><br>
                Total Paid: <strong style="color: var(--accent-cyan); font-size: 18px;">$${data.pricing_summary.total_price.toLocaleString(undefined, {minimumFractionDigits: 2})}</strong>
            </p>
        `;

        document.getElementById('confirmationModal').classList.add('active');
        fetchCruises(); // Refresh capacity badges
    } catch (err) {
        alert('Booking error: ' + err.message);
    }
}

function closeModal() {
    document.getElementById('confirmationModal').classList.remove('active');
}

function goToAuditFromModal() {
    closeModal();
    document.getElementById('lookupInput').value = state.lastBookingRef;
    switchTab('lookup');
    handleLookupSubmit();
}

// --- Lookup & Historical Audit ---
async function handleLookupSubmit() {
    const ref = document.getElementById('lookupInput').value.trim();
    if (!ref) return;

    const resultDiv = document.getElementById('auditResultContainer');
    resultDiv.innerHTML = `<p class="placeholder-text">Retrieving historical snapshot...</p>`;

    try {
        const response = await fetch(`/api/bookings/${ref}/reconstruct`);
        const data = await response.json();

        if (!response.ok) {
            resultDiv.innerHTML = `<div class="promo-feedback error" style="font-size: 16px;">❌ ${data.detail}</div>`;
            return;
        }

        const snap = data.itemized_snapshot;
        const ps = snap.pricing_summary;

        resultDiv.innerHTML = `
            <div class="audit-card">
                <div class="audit-header">
                    <div>
                        <h3 style="font-size: 20px; color: var(--text-bright);">Booking Ref: ${data.booking_reference}</h3>
                        <span style="font-size: 13px; color: var(--text-muted);">Stored Date: ${data.booking_created_at}</span>
                    </div>
                    <span class="verify-badge">VERIFIED SNAPSHOT MATCH</span>
                </div>

                <p style="margin-bottom: 16px; font-size: 14px; color: var(--text-muted);">
                    Ship: <strong>${snap.cruise.ship_name}</strong> (${snap.cruise.cruise_line}) • Destination: <strong>${snap.cruise.destination}</strong>
                </p>

                <div class="price-breakdown-list">
                    <div class="breakdown-row">
                        <span>Adult Base Fare Charged</span>
                        <span>$${ps.adult_subtotal.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                    <div class="breakdown-row">
                        <span>Child Fare Charged</span>
                        <span>+$${ps.child_subtotal.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                    <div class="breakdown-row subtotal">
                        <span>Gross Cruise Subtotal</span>
                        <span>$${ps.gross_cruise_subtotal.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                    ${ps.group_discount.amount > 0 ? `
                        <div class="breakdown-row discount-text">
                            <span>Group Discount (${ps.group_discount.percentage}%)</span>
                            <span>-$${ps.group_discount.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                        </div>
                    ` : ''}
                    <div class="breakdown-row">
                        <span>Services Subtotal</span>
                        <span>+$${ps.services_total_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                    ${ps.promo_code.discount_amount > 0 ? `
                        <div class="breakdown-row discount-text">
                            <span>Promo Discount (${ps.promo_code.applied_code})</span>
                            <span>-$${ps.promo_code.discount_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                        </div>
                    ` : ''}
                    <div class="breakdown-row">
                        <span>Tax (${ps.tax.percentage_label})</span>
                        <span>+$${ps.tax.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                    <div class="breakdown-row total">
                        <span>Reconstructed Historical Total</span>
                        <span>$${data.reconstructed_total.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                </div>
            </div>
        `;
    } catch (err) {
        resultDiv.innerHTML = `<div class="promo-feedback error">❌ Audit Error: ${err.message}</div>`;
    }
}

// --- Admin Controls ---
async function fetchAdminRules() {
    try {
        const response = await fetch('/api/admin/config');
        const data = await response.json();
        
        const container = document.getElementById('adminRulesContainer');
        container.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 16px;">
                <div>
                    <h4 style="color: var(--accent-cyan); margin-bottom: 8px;">Active Promo Codes</h4>
                    <ul style="font-size: 13px; color: var(--text-muted); list-style: none;">
                        ${data.promotional_codes.map(p => `<li>🔑 <strong>${p.code}</strong> - ${p.type} (${p.value}${p.type==='Percentage'?'%':'$'}) | Max Uses: ${p.current_total_uses}/${p.max_total_uses}</li>`).join('')}
                    </ul>
                </div>
                <div>
                    <h4 style="color: var(--accent-cyan); margin-bottom: 8px;">Child Age Bands</h4>
                    <ul style="font-size: 13px; color: var(--text-muted); list-style: none;">
                        ${data.child_age_bands.map(b => `<li>👶 Age ${b.min_age}-${b.max_age}: <strong>${b.fare_percentage}% of Adult Fare</strong></li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
    } catch (err) {
        console.error('Error loading admin rules:', err);
    }
}

async function handleAdminCreateCruise(event) {
    event.preventDefault();
    const payload = {
        cruise_line: document.getElementById('admLine').value,
        ship_name: document.getElementById('admShip').value,
        departure_port: document.getElementById('admPort').value,
        destination: document.getElementById('admDest').value,
        nights: parseInt(document.getElementById('admNights').value),
        adult_fare: parseFloat(document.getElementById('admFare').value),
        total_capacity: parseInt(document.getElementById('admCap').value)
    };

    const response = await fetch('/api/admin/cruises', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (response.ok) {
        alert('Cruise itinerary added successfully!');
        document.getElementById('adminCruiseForm').reset();
        fetchCruises();
    }
}

async function handleAdminCreatePromo(event) {
    event.preventDefault();
    const payload = {
        code: document.getElementById('admCode').value.toUpperCase(),
        type: document.getElementById('admType').value,
        value: parseFloat(document.getElementById('admValue').value),
        min_spend: parseFloat(document.getElementById('admMinSpend').value),
        valid_from: document.getElementById('admFrom').value,
        valid_to: document.getElementById('admTo').value,
        max_total_uses: parseInt(document.getElementById('admMaxTotal').value),
        max_uses_per_customer: parseInt(document.getElementById('admMaxUser').value)
    };

    const response = await fetch('/api/admin/promos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (response.ok) {
        alert('Promo code created successfully!');
        document.getElementById('adminPromoForm').reset();
        fetchAdminRules();
    }
}
